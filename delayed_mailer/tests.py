import logging
import sys
import unittest

import mock


from django.core import mail
from django.core.cache import cache
from django.test import RequestFactory
from delayed_mailer.log import DelayedEmailHandler, Group


def zero_error():
    try:
        1 / 0
    except ZeroDivisionError:
        return sys.exc_info()


def attribute_error():
    try:
        None.lower()
    except AttributeError:
        return sys.exc_info()


class Record(object):
    pass


@mock.patch('delayed_mailer.tasks.delayed_send.apply_async')
class TestDelayedMailer(unittest.TestCase):

    def setUp(self):
        cache.clear()
        mail.outbox = []
        self.record = Record()
        self.record.levelname = logging.DEBUG
        self.record.request = RequestFactory().get('/')
        self.record.msg = 'oops'
        self.record.exc_info = zero_error()
        self.handler = DelayedEmailHandler()

    def test_group_same(self, celery):
        args = [self.record.levelname, self.record.exc_info[0],
                self.record.exc_info[1]]
        gr1 = Group.find_group(*args)
        gr2 = Group.find_group(*args)
        assert gr1.hash == gr2.hash

    @mock.patch('delayed_mailer.log.Group.send')
    def test_single_emit(self, celery, send):
        self.handler.emit(self.record)
        assert send.called

    def test_single_delayed(self, celery):
        self.handler.emit(self.record)
        assert 'countdown' in celery.call_args[1]

    def test_count(self, celery):
        self.handler.emit(self.record)
        self.handler.emit(self.record)
        assert len(mail.outbox) == 0
        assert self.handler._group.count() == 2

    def test_reset(self, celery):
        self.handler.emit(self.record)
        self.handler._group.send()
        assert self.handler._group.count() == 0

    def test_mail_count(self, celery):
        self.handler.emit(self.record)
        self.handler._group.send()
        assert 'Error occurred:' not in mail.outbox[0].body

    def test_mail_count_multiple(self, celery):
        self.handler.emit(self.record)
        self.handler.emit(self.record)
        assert self.handler._group.count() == 2
        self.handler._group.send()
        assert len(mail.outbox) == 1
        assert 'Error occurred: 2' in mail.outbox[0].body
