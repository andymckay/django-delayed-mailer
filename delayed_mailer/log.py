import hashlib
import logging
import socket
import traceback

from django.conf import settings
from django.core import mail
from django.core.cache import cache

from delayed_mailer.tasks import delayed_send


class Group(object):
    """Group together errors using Django caching lib."""
    # TODO: raise an error if they are using something
    # like locmem, which won't work.
    key = 'delayed-mailer'

    def __init__(self, hash):
        self.hash = hash
        self.data_key = '%s-data:%s' % (self.key, self.hash)
        self.counter_key = '%s-count:%s' % (self.key, self.hash)

    def count(self):
        return cache.get(self.counter_key) or 0

    def set(self, data):
        if self.count():
            cache.incr(self.counter_key)
        else:
            # First setting of the task, write a celery task to post
            # this in DELAYED_MAILER_WAIT seconds.
            #
            # We force a timeout so that if the original post fails and
            # never goes out, eventually the cache will clear again and
            # we've lost a few errors.
            time = getattr(settings, 'DELAYED_MAILER_WAIT', 60)
            cache.set_many({self.data_key: data, self.counter_key: 1},
                           timeout=time * 2)
            # If memcached didn't get that, we can't do the async, it would
            # be nice if this didn't just fail silently.
            if not cache.get(self.data_key):
                self.send(count=1, msg=data)

            try:
                delayed_send.apply_async([self], countdown=time)
            except socket.error:
                # If the celery backend is down, we can't queue so just
                # send.
                self.send()

    @classmethod
    def get_hash(cls, *data):
        hash = hashlib.md5()
        hash.update(':'.join([str(d) for d in data]))
        return hash.hexdigest()

    @classmethod
    def find_group(cls, *data):
        return cls(cls.get_hash(*data))

    def send(self, count=1, msg=None):
        # If the data is not explicitly passed through, go and look for it
        # in memcache, then clean it out.
        if msg is None:
            data = cache.get_many([self.data_key, self.counter_key])
            if not data:
                return
            cache.delete_many([self.data_key, self.counter_key])
            count = data[self.counter_key]
            msg = data[self.data_key]

        if count > 1:
            msg['message'] = (
                u'Error occurred: %s times in the last %s seconds\n\n%s' % (
                    count, getattr(settings, 'DELAYED_MAILER_WAIT', 60),
                    msg['message']))

        mail.mail_admins(msg['subject'], msg['message'])


class DelayedEmailHandler(logging.Handler):

    def emit(self, record):
        try:
            request = record.request
            subject = '%s (%s IP): %s' % (
                record.levelname,
                (request.META.get('REMOTE_ADDR') in
                 settings.INTERNAL_IPS and 'internal' or 'EXTERNAL'),
                record.msg
            )
            request_repr = repr(request)
        except:
            subject = '%s: %s' % (
                record.levelname,
                record.msg
            )

            request = None
            request_repr = "Request repr() unavailable"

        if record.exc_info:
            exc_info = record.exc_info
            stack_trace = '\n'.join(traceback.format_exception(
                                    *record.exc_info))
        else:
            exc_info = (None, record.msg, None)
            stack_trace = 'No stack trace available'

        message = "%s\n\n%s" % (stack_trace, request_repr)

        self._group = Group.find_group([record.levelname,
                                        exc_info[0], exc_info[1]])
        self._group.set({'subject': subject, 'message': message})
