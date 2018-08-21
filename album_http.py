#!/bin/env python3
from twisted.internet import reactor
from twisted.internet.defer import DeferredList, succeed
from twisted.python import log, compat
from twisted.web.client import readBody, HTTPDownloader
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer

from urllib.parse import urlparse
from zope.interface import implementer
from pathlib import Path
from album_operation import AlbumOperation

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

class HttpAlbumOperation(AlbumOperation):
    def __init__(self, site, agent, dl_path):
        AlbumOperation.__init__(self, site, dl_path)
        self._agent = agent

    def _cbUpdateCookie(self, result):
        if result:
            self._agent.cookieJar.save()

        return

    def _cbBypassLoginMsg(self, response):
        d = self._agent.request(b'GET', self._site.memberURL())
        d.addCallback(readBody)
        d.addCallback(self._site.isValidUser)
        d.addCallback(self._cbUpdateCookie)
        return d

    def _cbPostLoginRequest(self, query):
        body = BytesProducer(query)

        d = self._agent.request(b'POST', self._site.memberURL(),
                Headers(
                    {'Content-Type':
                    ['application/x-www-form-urlencoded'],
                    # The future cookie would apply the language
                    # setting here
                    'Accept-Language':
                    ['en-US,en', 'q=0.5']}
                    ),
                body
                )
        d.addCallback(self._cbBypassLoginMsg)

        return d

    def _cbReqAlbumPage(self, response):
        d = readBody(response)

        d.addCallback(self._site.parseAlbumPage)
        d.addErrback(self._ebSiteParseAlbum)
        d.addCallback(self._cbPrepareLocalAlbum)

        return d

    def _cbGetPhotoDlLink(self, response, view_url):
        d = readBody(response)

        d.addCallback(self._site.extractLinkFromPhotoPage)
        d.addErrback(log.err)
        d.addCallback(self._site.generatePhotoDLInfo, *[view_url])
        d.addErrback(log.err)

        return d

    def _cbDownloadPhoto(self, link_data):
        d = self._agent.request(b'GET', link_data.get('url'),
                Headers({'Referer': link_data.get('referer') })
                )
        d.addCallback(readBody)
        d.addCallback(self._cbDownloadComplete, *[link_data.get('file_name')])

        return d

    def _cbReqPhotoPage(self, photo_list):
        def photoConnectLost(message, url):
            log.err(message)
            raise Exception("can't access {0!s}".format(url))

        dl = []
        for i in photo_list:
            d = self._agent.request(b'GET', bytes(i.get('url'), 'ascii'))
            d.addCallback(self._cbGetPhotoDlLink, *[i.get('url')])
            d.addErrback(photoConnectLost, *[i.get('url')])
            d.addCallback(self._cbDownloadPhoto)
            d.addErrback(log.err)
            dl.append(d)
            if len(dl) > 16:
                deferreds = DeferredList(dl, consumeErrors=True)
                dl = []

    def _cbUserLogin(self, login_state):
        if login_state is not True:
            d = self._agent.request(b'GET', self._site.memberURL())
            d.addCallback(readBody)
            d.addCallback(self._site.generateLoginForm)
            d.addErrback(log.err)
            d.addCallback(self._cbPostLoginRequest)
            d.addErrback(log.err)

            return d

        return login_state

    def startUserLogin(self):
        d = self._agent.request(b'GET', self._site.memberURL())
        d.addCallback(readBody)
        d.addCallback(self._site.isValidUser)
        d.addCallback(self._cbUserLogin)
        return d

    def startDownloadAlbum(self, url):
        d = self._agent.request(b'GET', self._site.rewriteURL(url))
        d.addCallback(self._cbReqAlbumPage)
        d.addErrback(self._ebDownloadAlbum)
        d.addCallback(self._cbReqPhotoPage)
        d.addErrback(log.err)

        return d
