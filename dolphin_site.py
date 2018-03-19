#!/bin/env python3
# The html parser for Boonex Dolphin Pro

from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlencode
import re

def the_raw_download_button(title):
    return title and re.compile("RAW").search(title)

class DolphinSite(object):
    def __init__(self, config):
        self.site_url = config.get('url')
        self.username = config.get('username')
        self.password = config.get('password')

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
        req = urlparse(self.site_url)
        req = req._replace(path='/member.php')

        return bytes(req.geturl(), 'ascii')
    
    def isValidUser(self, body):
        soup = BeautifulSoup(body, 'html.parser')
        try:
            profile = soup.find(class_='sys-sm-profile')
            user_name = profile.find(class_="sys-smp-title")
        except AttributeError:
            return False

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
                'relocate': self.site_url,
                'rememberMe': 'on',
                'csrf_token': csrf_token,
                'ID': self.username,
                'Password': self.password,
                }

        query = urlencode(values, doseq=True)
        return query

    def extractPhotoPages(self, soup):
        try:
            result_b = soup.find(class_="result_block")
            files_res = result_b.find_all(class_="sys_file_search_title")
        except AttributeError as e:
            print("invalid search request for the album")
            raise e
        if len(files_res) == 0:
            print("No photo in this ablum")
            raise Exception

        p_list = []
        for i in files_res:
            photo_name = i.string
            photo_url = i.a.get('href')
            p_list.append({'name': photo_name, 'url': photo_url})

        return p_list

    def parseAlbumPage(self, body):
        soup = BeautifulSoup(body, 'html.parser')
        page_c1 = soup.find(id="page_column_1")
        title_tag = page_c1.find(class_="dbTitle")
        title_value = title_tag.contents[0]
        ablum_name = re.findall('"([^"]*)"', title_value)[0]

        photo_pages = self.extractPhotoPages(soup)

        return {'name': ablum_name, 'photos': photo_pages}

    def extractLinkFromPhotoPage(self, body):
        soup = BeautifulSoup(body, 'html.parser')

        # TODO: support JPEG file
        button = soup.find("button", class_="menuLink",
                           title=the_raw_download_button)
        file_title = soup.find("div", class_="fileTitle")
        name = file_title.contents[0].strip()

        if button:
            photo_url = button.attrs['onclick']
            photo_url = re.findall("([^']*)'", photo_url)[1]
            photo_url = bytes(photo_url, 'ascii')
            return {'name': name, 'url': photo_url}

        raise Exception

    def generatePhotoDLInfo(self, photo_data, parent_url):
        return { 'url': photo_data.get('url'),
                'file_name': photo_data.get('name'),
                'referer': [ bytes(parent_url, 'ascii')],
                'user': self.username,
                'pass': self.password,
                }
