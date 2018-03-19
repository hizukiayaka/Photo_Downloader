#!/bin/env python3
import sys
from twisted.internet import reactor
from twisted.python import log, compat
from twisted.web.client import Agent, CookieAgent
from twisted.web.client import HTTPConnectionPool

from urllib.parse import urlparse
from http.cookiejar import LWPCookieJar

from config import read_config
from dolphin_site import DolphinSite
from album_http import HttpAlbumOperation, cbShutdown

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

    site = DolphinSite(config.get(netloc))
    ablum = HttpAlbumOperation(site, agent, save_path)

    d = ablum.DownloadRestrictedAlbum(url)
    # FIXME: it doesn't work
    #d.addCallback(cbShutdown)

    reactor.run()

if __name__ == "__main__":
    main()
