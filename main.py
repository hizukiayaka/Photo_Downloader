#!/bin/env python3
from twisted.internet import reactor
from twisted.python import log, compat
from twisted.web.client import Agent, CookieAgent
from twisted.web.client import HTTPConnectionPool
import sys

from urllib.parse import urlparse
from http.cookiejar import LWPCookieJar
from config import read_config
from dolphin_album import DolphinAlbum
from network import (
    cb_post_login_request,
    cbDownloadPhoto,
    cbShutdown,
    user_session,
    request_photo_page,
    )

def main():
    if len(sys.argv) > 1:
        url = sys.argv[1]
    if url is None:
        return

    if len(sys.argv) > 2:
        save_path = sys.argv[2]
    else:
        save_path = "Downloads"

    o = urlparse(url)
    if len(o[1]):
        netloc = o[1]
    else:
        return

    config = read_config()
    if config.get(netloc) is None:
        return
   
    cookieJar = LWPCookieJar('photo.cookie')
    cookieJar.load()

    pool = HTTPConnectionPool(reactor)
    agent = CookieAgent(Agent(reactor, pool=pool), cookieJar)

    album = DolphinAlbum(config.get(netloc))
    ud = user_session(agent, album)

    d = agent.request(b'GET', album.rewriteURL(url))

    d.addCallback(album.cbRequestAlbumPage)
    d.addErrback(log.err)
    d.addCallback(request_photo_page, *[agent, album])
    d.addErrback(log.err)
    d.addCallback(cbShutdown)


    reactor.run()

if __name__ == "__main__":
    main()
