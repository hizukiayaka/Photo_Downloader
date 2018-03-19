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

class HttpAlbumOperation(object):
    def __init__(self, site, agent, dl_path):
        self.site = site
        self.agent = agent
        self.dl_path = Path(dl_path)
        self.album_dl_path = self.dl_path

    def cbUpdateCookie(self, result):
        if result:
            self.agent.cookieJar.save()

        return

    def cbBypassLoginMsg(self, response):
        d = self.agent.request(b'GET', self.site.memberURL())
        d.addCallback(readBody)
        d.addCallback(self.site.isValidUser)
        d.addCallback(self.cbUpdateCookie)
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

    def cbPrepareLocalAlbum(self, album_data):
        album_name = Path(album_data.get('name'))
        album_dir = self.dl_path.joinpath(album_name)
        try:
            album_dir.mkdir()
        except FileExistsError:
            pass
        except FileNotFoundError as e:
            log.err("can't create the directory {}".format(album_dir))
            raise e

        self.album_dl_path = album_dir

        return album_data.get('photos')

    def cbReqAlbumPage(self, response):
        d = readBody(response)

        d.addCallback(self.site.parseAlbumPage)
        d.addErrback(log.err)
        d.addCallback(self.cbPrepareLocalAlbum)
        d.addErrback(log.err)

        return d

    def cbGetPhotoDlLink(self, response, view_url):
        d = readBody(response)

        d.addCallback(self.site.extractLinkFromPhotoPage)
        d.addErrback(log.err)
        d.addCallback(self.site.generatePhotoDLInfo, *[view_url])
        d.addErrback(log.err)

        return d

    def cbDownloadComplete(self, body, file_name):
        p = self.album_dl_path.joinpath(file_name)
        with p.open(mode='w+b') as f:
            f.write(body)
        print("Download Complete")

    def ebDownloadError(failure):
        print("Download failure")

    def cbDownloadPhoto(self, link_data):
        d = self.agent.request(b'GET', link_data.get('url'),
                Headers({'Referer': link_data.get('referer') })
                )
        d.addCallback(readBody)
        d.addCallback(self.cbDownloadComplete, *[link_data.get('file_name')])

        return d

    def cbReqPhotoPage(self, photo_list):
        dl = []
        for i in photo_list:
            d = self.agent.request(b'GET', bytes(i.get('url'), 'ascii'))
            d.addCallback(self.cbGetPhotoDlLink, *[i.get('url')])
            d.addErrback(log.err)
            d.addCallback(self.cbDownloadPhoto)
            d.addErrback(log.err)
            dl.append(d)
        deferreds = DeferredList(dl, consumeErrors=True)
        # FIXME
        deferreds.addCallback(cbShutdown)

        return deferreds

    def cbUserLogin(self, login_state):
        if login_state is not True:
            d = self.agent.request(b'GET', self.site.memberURL())
            d.addCallback(readBody)
            d.addCallback(self.site.generateLoginForm)
            d.addErrback(log.err)
            d.addCallback(self.cbPostLoginRequest)
            d.addErrback(log.err)

            return d

        return login_state

    def startUserLogin(self):
        d = self.agent.request(b'GET', self.site.memberURL())
        d.addCallback(readBody)
        d.addCallback(self.site.isValidUser)
        d.addCallback(self.cbUserLogin)
        return d

    def startDownloadAlbum(self, url):
        d = self.agent.request(b'GET', self.site.rewriteURL(url))
        d.addCallback(self.cbReqAlbumPage)
        d.addErrback(log.err)
        d.addCallback(self.cbReqPhotoPage)
        d.addErrback(log.err)

        return d

    def cbPassAuth(self, auth_result, url):
        return self.startDownloadAlbum(url)

    def DownloadRestrictedAlbum(self, url):
        auth = self.startUserLogin()
        return auth.addCallback(self.cbPassAuth, *[url])

def cbShutdown(ignored):
    reactor.stop()
