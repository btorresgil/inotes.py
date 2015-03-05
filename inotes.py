#!/usr/bin/python
#
# iNotes.py - an Apple iCloud client for Python environments
#
# Author: Xavier Mertens <xavier@rootshell.be>
# Copyright: GPLv3 (http://gplv3.fsf.org/)
# Feel free to use the code, but please share the changes you've made
# 

import imaplib
import time
import ConfigParser
import email.message
import os
import sys
import logging
from optparse import OptionParser
from HTMLParser import HTMLParser

defaultConfigFile = '~/inotes.conf'

# Activate NullHandler logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def remove_html_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def connect_imap(configfile):
    # Read configuration file
    config = ConfigParser.ConfigParser()
    config.read(configfile)
    hostname = config.get('icloud', 'hostname')
    username = config.get('icloud', 'username')
    password = config.get('icloud', 'password')

    # Open an IMAP connection
    logger.debug('+++ Connecting to %s' % hostname)
    connection = imaplib.IMAP4_SSL(hostname)

    # Authenticate
    logger.debug('+++ Logging in as %s' % username)
    connection.login(username, password)
    return connection


def countnotes(configfile):
    c = connect_imap(configfile)
    try:
        typ, data = c.select('Notes', readonly=True)
        nbMsgs = int(data[0])
        logger.debug('You have %d available notes.' % nbMsgs)
    finally:
        try:
            c.close()
        except:
            pass
        c.logout()
    return


def listnotes(configfile):
    c = connect_imap(configfile)
    try:
        typ, data = c.select('Notes', readonly=True)
        typ, [ids] = c.search(None, 'ALL')
        for id in ids.split():
            typ, data = c.fetch(id, '(RFC822)')
            for d in data:
                if isinstance(d, tuple):
                    msg = email.message_from_string(d[1])
                    print msg['subject']
    finally:
        try:
            c.close()
        except:
            pass
        c.logout()
    return


def searchnotes(configfile, queryString, stripHtml):
    c = connect_imap(configfile)
    result = []
    try:
        typ, data = c.select('Notes', readonly=True)
        query = '(OR TEXT "%s" SUBJECT "%s")' % (queryString, queryString)
        typ, [ids] = c.search(None, query)
        for id in ids.split():
            typ, data = c.fetch(id, '(BODY[HEADER.FIELDS (SUBJECT)] BODY[TEXT])')
            print data[0][1].strip()
            print "---"
            if stripHtml:
                print remove_html_tags(data[1][1])
            else:
                print data[1][1]
    finally:
        try:
            c.close()
        except:
            pass
        c.logout()
    return


def createnote(configfile, subject, savehtml):
    c = connect_imap(configfile)
    try:
        # Read configuration file
        config = ConfigParser.ConfigParser()
        config.read(configfile)
        username = config.get('server', 'username')

        logger.debug("+++ Type your note and exit with CTRL-D")
        if savehtml:
            body = '<html>\n<head></head>\n<body>'
            for line in sys.stdin.readlines():
                body += line
                body += '<br>'
            body += '</body></html>'
        else:
            body = ''
            for line in sys.stdin.readlines():
                body += line

        now = time.strftime('%a, %d %b %Y %H:%M:%S %z')
        note = "Date: %s\nFrom: %s@me.com\nX-Uniform-Type-Identifier: com.apple.mail-note\nContent-Type: text/html;\nSubject: %s\n\n%s" % (
        now, username, subject, body)
        c.append('Notes', '', imaplib.Time2Internaldate(time.time()), str(note))

    finally:
        try:
            c.close()
        except:
            pass
        c.logout()

    return


def main(argv):

    parser = OptionParser(usage="usage: %prog [options]", version="%prog 1.0")
    parser.add_option('-c', '--config', dest='configfile', type='string',
                      help='specify the configuration file')
    parser.add_option('-C', '--count', action='store_true', dest='count',
                      help='count the number of notes')
    parser.add_option('-d', '--debug', action='store_true', dest='debug',
                      help='display this message')
    parser.add_option('-H', '--html', action='store_true', dest='saveHtml',
                      help='save the new note in HTML format')
    parser.add_option('-l', '--list', action='store_true', dest='list',
                      help='list saved notes')
    parser.add_option('-q', '--query', dest='query', type='string',
                      help='search fo keyword in saved notes')
    parser.add_option('-s', '--subject', dest='subject', type='string',
                      help='create a new note with subject')
    parser.add_option('-S', '--striphtml', action='store_true', dest='stripHtml',
                      help='remove HTML tags from displayed notes')
    (options, args) = parser.parse_args()
    rootLogger = logging.getLogger()
    consoleHandler = logging.StreamHandler()
    rootLogger.addHandler(consoleHandler)
    rootLogger.setLevel(logging.INFO)
    if options.debug:
        rootLogger.setLevel(logging.DEBUG)
        logger.debug('+++ Debug mode')
    if options.configfile is None:
        if not os.path.isfile(defaultConfigFile):
            print 'Cannot open ' + defaultConfigFile + '. Use the -c switch to provide a valid configuration.'
            sys.exit(1)
        configfile = defaultConfigFile
    else:
        configfile = options.configfile
    logger.debug('+++ Configuration file: %s', configfile)

    if options.count:
        countnotes(configfile)
    elif options.list:
        listnotes(configfile)
    elif options.query is not None:
        searchnotes(configfile, options.query, options.stripHtml)
    else:
        createnote(configfile, options.subject, options.saveHtml)


if __name__ == '__main__':
    main(sys.argv[1:])
    sys.exit()
