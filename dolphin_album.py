#!/bin/env python3
# The html parser for Boonex Dolphin Pro

from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlencode
from twisted.web.client import readBody
import re

def the_raw_download_button(title):
    return title and re.compile("RAW").search(title)

class DolphinAlbum:
    def __init__(self, config):
        self.url = config.get('url')
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
    
    def isValidUser(self, response):
        soup = BeautifulSoup(response, 'html.parser')
        profile = soup.find(class_='sys-sm-profile')
        user_name = profile.find(class_="sys-smp-title")

        if re.compile('Join or Login').search(user_name.string):
            print("not login")
            with open('result.html', "wb") as f:
                f.write(response)
            return False
        else:
            print("login as user: {}".format(user_name.string))

        return True

    def cbIsValidUser(self, response):
        d = readBody(response)
        d.addCallback(self.isValidUser)
        return d

    def postLoginUser(self, response):
        soup = BeautifulSoup(response, 'html.parser')
        csrf_form = soup.find("input", attrs={"name": "csrf_token"})
        csrf_token = csrf_form.attrs.get('value')

        values = {
                'relocate': 'https://www.insoler.com/',
                'rememberMe': 'on',
                'csrf_token': csrf_token,
                'ID': self.username,
                'Password': self.password,
                }

        query = urlencode(values, doseq=True)
        return query

    def cbPostLoginUser(self, response):
        d = readBody(response)
        d.addCallback(self.postLoginUser)
        return d

    def memberURL(self, url):
        req = urlparse(url)
        req = req._replace(path='/member.php')

        return bytes(req.geturl(), 'ascii')
 
    def extractPhotoPages(self, soup):
        result_b = soup.find(class_="result_block")
        files_res = result_b.find_all(class_="sys_file_search_title")
        p_list = []
        for i in files_res:
            photo_name = i.string
            photo_url = i.a.get('href')
            p_list.append({'name': photo_name, 'url': photo_url})

        return p_list

    def parseAlbumPage(self, response):
        soup = BeautifulSoup(response, 'html.parser')
        page_c1 = soup.find(id="page_column_1")
        the_title = page_c1.find(class_="dbTitle")

        return self.extractPhotoPages(soup)

    def cbRequestAlbumPage(self, response):
        d = readBody(response)
        d.addCallback(self.parseAlbumPage)
        return d

    def parseDlFromPhotoPage(self, response):
        soup = BeautifulSoup(response, 'html.parser')

        button = soup.find("button", class_="menuLink",
                           title=the_raw_download_button)
        if button:
            photo_url = button.attrs['onclick']
            photo_url = re.findall("([^']*)'", photo_url)[1]
            return photo_url

        return None
   
    def cbGetPhotoDlLink(self, response):
        d = readBody(response)
        d.addCallback(self.parseDlFromPhotoPage)
        return d
