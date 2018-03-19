#!/bin/env python3
from twisted.internet import reactor
from twisted.python import log, compat
from twisted.web.client import readBody
from twisted.internet.defer import DeferredList

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

class AlbumOperation(object):
    def __init__(self, site, agent):
        self.site = site
        self.agent = agent

    def cbIsValidUser(self, response):
        d = readBody(response)
        d.addCallback(self.site.isValidUser)
        return d

    def cbBypassLoginMsg(self, response):
        d = self.agent.request(b'GET', self.site.memberURL())
        d.addCallback(self.cbIsValidUser)
        return d

    def cbGenerateLoginData(self, response):
        d = readBody(response)
        d.addCallback(self.site.generateLoginData)
        return d

    def cbPostLoginRequest(self, query):
        body = BytesProducer(query)

        d = self.agent.request(b'POST', self.site.memberURL(),
                Headers(
                    {'Content-Type':
                    ['application/x-www-form-urlencoded']}
                    ),
                body
                )
        d.addCallback(self.cbBypassLoginMsg)

        return d

    def cbRequestAlbumPage(self, response):
        d = readBody(response)

        d.addCallback(self.site.parseAlbumPage)
        d.addErrback(log.err)

        return d

    def cbGetPhotoDlLink(self, response, view_url):
        d = readBody(response)

        d.addCallback(self.site.extractLinkFromPhotoPage)
        d.addErrback(log.err)
        d.addCallback(self.site.generatePhotoDLInfo, *[view_url])
        d.addErrback(log.err)

        return d

    def cbReqPhotoPage(self, photo_list):
        if isinstance(photo_list, list) and len(photo_list) > 0:
            dl = []
            for i in photo_list:
                d = self.agent.request(b'GET', bytes(i.get('url'), 'ascii'))
                d.addCallback(self.cbGetPhotoDlLink, *[i.get('url')])
                d.addCallback(cbDownloadPhoto)
                dl.append(d)
            deferreds = DeferredList(dl, consumeErrors=True)

            return deferreds.addCallback(cbShutdown)
        else:
            reactor.stop()

    def startAuth(self):
        d = self.agent.request(b'GET', self.site.memberURL())

        d.addCallback(self.cbGenerateLoginData)
        d.addErrback(log.err)
        d.addCallback(self.cbPostLoginRequest)
        d.addErrback(log.err)

        return d

    def startDownloadAlbum(self, url):
        d = self.agent.request(b'GET', self.site.rewriteURL(url))
        d.addCallback(self.cbRequestAlbumPage)
        d.addErrback(log.err)
        d.addCallback(self.cbReqPhotoPage)
        d.addErrback(log.err)

def cbDownloadPhoto(link_data):
    print("URL: {}".format(link_data.get('url')))
    print("HTTP referer: {}".format(link_data.get('referer')))

    return True

def cbShutdown(ignored):
    reactor.stop()
