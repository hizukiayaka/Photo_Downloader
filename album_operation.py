#!/bin/env python3
from twisted.python import log, compat

from urllib.parse import urlparse
from pathlib import Path

class AlbumOperation(object):
    def __init__(self, site, dl_path):
        self._site = site
        self._dl_path = Path(dl_path)
        self._album_dl_path = self._dl_path

    def _cbPrepareLocalAlbum(self, album_data):
        a_name = album_data.get('name')

        album_path = Path(a_name)
        album_dir = self._dl_path.joinpath(album_path)

        for i in range(4, len(album_data.get('name')), 4):
            try:
                album_dir.mkdir()
            except FileExistsError:
                break
            except FileNotFoundError as e:
                log.err("can't create the directory {}".format(album_dir))
                raise
            except OSError:
                s_name = a_name[:len(a_name) - i]
                s_name += "_$"
                album_dir = self._dl_path.joinpath(s_name)
                continue
            break

        if album_dir.exists():
            self._album_dl_path = album_dir
        else:
            raise Exception("Can't prepare the local album directory")

        return album_data.get('photos')

    def _ebSiteParseAlbum(self, failure):
        log.err(failure)
        raise Exception("can't parse the request URL as an album")

    def _cbDownloadComplete(self, data, file_name):
        p = self._album_dl_path.joinpath(file_name)
        with p.open(mode='w+b') as f:
            f.write(data)
        log.msg("Download Complete")

    def _ebDownloadError(failure):
        log.err(failure)

    def _ebDownloadAlbum(self, failure):
        log.err(failure)
        raise Exception("can't handle the request URL")

    def _cbPassAuth(self, auth_result, url):
        return self.startDownloadAlbum(url)

    def DownloadRestrictedAlbum(self, url):
        auth = self.startUserLogin()
        auth.addCallback(self._cbPassAuth, *[url])
        auth.addErrback(log.err)

        return auth
