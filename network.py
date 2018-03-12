from twisted.internet import reactor
from twisted.python import log, compat
from twisted.web.client import Agent, CookieAgent

from cookielib import FileCookieJar
from config import read_config

def user_session(agent, config):
    d = agent.request(b'GET', config.get('url'))

def main():
    url = sys.argv[1]
    if url is None:
        return

    cookieJar = FileCookieJar('photo.cookie')
    cookieJar.load()
    agent = CookieAgent(Agent(reactor), cookieJar)

    config = read_config()
    user_session(agent, config.get(i))

    finished = Deferred()
    d = agent.request(album_url_rewrite(url))
    d.addCallBack(DolphinPhotoAlbum(finished, save_path))

    cookieJar.save()
