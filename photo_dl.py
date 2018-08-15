#!/bin/env python3

from twisted.internet import reactor
from twisted.internet.defer import DeferredList
from twisted.python import log, compat
from twisted.web.client import Agent, CookieAgent
from twisted.web.client import HTTPConnectionPool

from argparse import ArgumentParser
from urllib.parse import urlparse
from http.cookiejar import LWPCookieJar
from config import read_config
from dolphin_site import DolphinSite
from album_http import HttpAlbumOperation

def cbShutdown(ignored):
    reactor.stop()

def prepareNetwork():
    cookieJar = LWPCookieJar('photo.cookie')
    cookieJar.load()

    pool = HTTPConnectionPool(reactor, persistent=True)
    pool.maxPersistentPerHost = 15
    agent = CookieAgent(Agent(reactor, pool=pool), cookieJar)

    return agent

def processULR(agent, url, save_path):
    o = urlparse(url)
    if len(o[1]):
        netloc = o[1]
    else:
        return

    config = read_config()
    if config.get(netloc) is None:
        return
   
    site = DolphinSite(config.get(netloc))
    ablum = HttpAlbumOperation(site, agent, save_path)

    d = ablum.DownloadRestrictedAlbum(url)

    return d

def main():
    parser = ArgumentParser()
    parser.add_argument('url', nargs='?', default=None, help="the album's url")
    parser.add_argument('-f', '--file', help="A albums list file")
    parser.add_argument('-d', '--download', help="The path storing the ablum",
                        default="Downloads")

    album_tasks = []
    args = parser.parse_args()
    agent = prepareNetwork()

    if args.url:
        album_tasks.append(processULR(agent, args.url, args.download))

    if args.file:
        with open(args.file, 'r') as f:
            for i in f:
                album_tasks.append(processULR(agent, i.strip(), args.download))

    deferreds = DeferredList(album_tasks, consumeErrors=True)
    deferreds.addCallback(cbShutdown)

    reactor.run()

if __name__ == "__main__":
    main()
