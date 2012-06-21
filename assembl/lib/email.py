""" Email-related utilities. """

from __future__ import absolute_import

from datetime import datetime, timedelta
import email
import re

from pyramid.settings import asbool

from .vendor import imaplib2


class MailboxSelectionError(Exception):
    pass


class IMAP4Mailbox(object):
    """ Manages an IMAP4 mailbox. """

    def __init__(self, host=None, port=None, ssl=False, username=None,
                 password=None, mailbox='INBOX', settings=None):
        """ Create an mailbox handler from either app config or kwargs. """
        def config(key, arg):
            return settings.get('assembl.imap4.%s' % key) if settings else arg
        self._connection = None
        self._mailbox_selected = False
        self.host = config('host', host)
        self.port = int(config('port', port) or 143)
        self.ssl = asbool(config('ssl', ssl))
        self.username = config('username', username)
        self.password = config('password', password)
        self.mailbox = config('mailbox', mailbox)

    @property
    def connection(self):
        if self._connection is None:
            imap_cls = imaplib2.IMAP4_SSL if self.ssl else imaplib2.IMAP4
            self._connection = imap_cls(self.host, self.port)
            self._connection.login(self.username, self.password)
            code, [msg] = self._connection.select(self.mailbox)
            if not code == 'OK':
                raise MailboxSelectionError(msg)
            self._mailbox_selected = True
        return self._connection

    def close(self):
        if self._connection is not None:
            if self._mailbox_selected:
                self._connection.close()
                self._mailbox_selected = False
            self._connection.logout()

    @property
    def messages(self):
        """ Return a generator that iterates through all mailbox messages. """
        typ, [msg_ids] = self.connection.search(None, 'ALL')
        iter_matches = re.finditer(r'\w+', msg_ids)
        for match in iter_matches:
            code, msg_data = self.connection.fetch(match.group(0), '(RFC822)')
            yield email.message_from_string(msg_data[0][1])


def parsedate(date_string):
    """ Make a UTC (but naive) datetime object from an RFC2822 string. """
    struct_time = email.utils.parsedate_tz(date_string)
    try:
        timezone = struct_time[-1] or 0
        return datetime(*list(struct_time[:6])) - timedelta(seconds=timezone)
    except:
        raise ValueError('Error parsing date. Make sure to provide an RFC2822 '
                         'date string.')