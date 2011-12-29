import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.test import RequestFactory

from delayed_mailer.log import DelayedEmailHandler
from delayed_mailer.tests import Record, attribute_error, zero_error


class Command(BaseCommand):
    help = ('Simulate using the delayed mailer so you can check queues '
            'caches and so on are set up correctly.')

    def handle(self, *args, **kw):
        wait = getattr(settings, 'GROUP_WAIT')
        if not wait:
            print 'No GROUP_WAIT setting, using value of 2 seconds.'
        else:
            print ('GROUP_WAIT setting being changed temporarily to 2 '
                   'seconds from %s seconds.' % wait)
        settings.GROUP_WAIT = 2

        self.record = Record()
        self.record.levelname = logging.DEBUG
        self.record.request = RequestFactory().get('/')
        self.record.msg = 'This error should have occured 2x'
        self.record.exc_info = zero_error()

        for x in xrange(2):
            self.handler = DelayedEmailHandler()
            self.handler.emit(self.record)

        self.record.msg = 'This error should occur 1x'
        self.record.exc_info = attribute_error()
        self.handler = DelayedEmailHandler()
        self.handler.emit(self.record)

        print 'You should have 2 emails for 3 errors.'
