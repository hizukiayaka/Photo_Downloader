#!/bin/env python3
# The html parser for Boonex Dolphin Pro

from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlencode
import re

class DolphinSite(object):
    def __init__(self, config):
        self._site_url = config.get('url')
        self._username = config.get('username')
        self._password = config.get('password')

    def rewriteURL(self, url):
        req_path = urlparse('?'.join(urlparse(url).path.split('&', 1)))
        req_host = urlparse(url)

        req = req_path._replace(scheme=req_host.scheme)
        req = req._replace(netloc=req_host.netloc)
        req = req._replace(params=req_host.params)
        req = req._replace(query="per_page=2000")
        req = req._replace(fragment=req_host.fragment)

        return bytes(req.geturl(), 'ascii')

     # TODO
    def memberURL(self):
        req = urlparse(self._site_url)
        req = req._replace(path='/member.php')

        return bytes(req.geturl(), 'ascii')
    
    def isValidUser(self, body):
        soup = BeautifulSoup(body, 'html.parser')
        try:
            profile = soup.find(class_='sys-sm-profile')
            user_name = profile.find(class_="sys-smp-title")
        except AttributeError:
            raise AttributeError("can't find user profile")

        if re.compile('Join or Login').search(user_name.string):
            return False

        return True

    def generateLoginForm(self, body):
        soup = BeautifulSoup(body, 'html.parser')
        try:
            csrf_form = soup.find("input", attrs={"name": "csrf_token"})
            csrf_token = csrf_form.attrs.get('value')
        except AttributeError:
            csrf_form = ""
            csrf_token = ""

        values = {
                'relocate': self._site_url,
                'rememberMe': 'on',
                'csrf_token': csrf_token,
                'ID': self._username,
                'Password': self._password,
                }

        query = urlencode(values, doseq=True)
        return query

    def _extractPhotoPages(self, soup):
        try:
            # FIXME
            result_b = soup.find("div", class_="boxContent")
            files_res = result_b.find_all(class_="sys_file_search_title")
        except AttributeError:
            raise AttributeError("invalid search request for the album")
        if len(files_res) == 0:
            raise Exception("No photo in this album")

        p_list = []
        for i in files_res:
            photo_name = i.string
            photo_url = i.a.get('href')
            p_list.append({'name': photo_name, 'url': photo_url})

        return p_list

    def parseAlbumPage(self, body):
        def thePhotoColumn(contents):
            return (contents is not None
                    and re.compile("Browse photos from album").
                    search(contents[0]) is not None)

        def thePhotoResultColumn(data):
            for j in data:
                if (thePhotoColumn(j.contents)):
                        t_value = j.contents[0]
                        album_name = re.findall('"([^"]*)"', t_value)[0]
                        return album_name
            return False

        soup = BeautifulSoup(body, 'html.parser')
        try:
            page_c1s = soup.find_all(id="page_column_1")
            for i in page_c1s:
                title_tags = i.find_all(class_="dbTitle")
                album_name = thePhotoResultColumn(title_tags)
                if album_name:
                    page_c1 = i
                    break

            photo_pages = self._extractPhotoPages(page_c1)
            return {'name': album_name, 'photos': photo_pages}

        except NameError:
            raise Exception("The request url doesn't match the site settings")
        except AttributeError:
            raise AttributeError("The request url doesn't match the site settings")

    def extractLinkFromPhotoPage(self, body):
        def theDownloadButton(title):
            return title and re.compile("Download").search(title)

        soup = BeautifulSoup(body, 'html.parser')

        button = soup.find("button", class_="menuLink",
                           title=theDownloadButton)
        file_title = soup.find("div", class_="fileTitle")
        name = file_title.contents[0].strip()

        if button:
            photo_url = button.attrs['onclick']
            photo_url = re.findall("([^']*)'", photo_url)[1]
            photo_url = bytes(photo_url, 'ascii')
            return {'name': name, 'url': photo_url}

        raise Exception("No download link")

    def generatePhotoDLInfo(self, photo_data, parent_url):
        return { 'url': photo_data.get('url'),
                'file_name': photo_data.get('name'),
                'referer': [ bytes(parent_url, 'ascii')],
                'user': self._username,
                'pass': self._password,
                }
