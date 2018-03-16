#!/bin/env python3
from twisted.internet import reactor
from twisted.python import log, compat
from twisted.web.client import readBody

from urllib.parse import urlparse

from twisted.web.iweb import IBodyProducer
from zope.interface import implementer
from twisted.web.http_headers import Headers
from twisted.internet.defer import succeed

@implementer(IBodyProducer)
class BytesProducer(object):
    def __init__(self, body):
        self.body = bytes(body, 'ascii')
        self.length = len(self.body)
    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)
    def pauseProducing(self):
        pass
    def stopProducing(self):
        pass

def cb_post_login_request(query, agent, album):
    body = BytesProducer(query)
    d = agent.request(b'POST', album.memberURL(album.url),
            Headers({}),
            body
            )
    d.addCallback(album.cbIsValidUser)

def cbDownloadPhoto(url):
    print(url)

def cbShutdown(ignored):
    reactor.stop()

def user_session(agent, album):
    d = agent.request(b'GET', album.memberURL(album.url))
    d.addCallback(album.cbPostLoginUser)
    d.addErrback(log.err)
    d.addCallback(cb_post_login_request, *[agent, album])

    return d

def request_photo_page(photo_list, agent, album):
    if isinstance(photo_list, list) and len(photo_list) > 0:
        for i in photo_list:
            d = agent.request(b'GET', bytes(i.get('url'), 'ascii'))
            d.addCallback(album.cbGetPhotoDlLink)
            d.addCallback(cbDownloadPhoto)
    else:
        reactor.stop()
