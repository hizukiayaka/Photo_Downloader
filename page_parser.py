#!/bin/env python3

from urllib.request import urlopen
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import re

def the_raw_download_button(title):
    return title and re.compile("RAW").search(title)

def photo_download(url, path, name):
   page = urlopen(url);
   soup = BeautifulSoup(page, 'html.parser')

   button = soup.find("button", class_="menuLink", title=the_raw_download_button)
   if button:
       photo_url = button.attrs['onclick']
       photo_url = re.findall("([^']*)'", photo_url)[1]
       print(photo_url)

def photo_from_album(photos, path):
   for i in photos:
      photo_name = i.string
      photo_url = i.a.get('href')

      photo_download(photo_url, path, photo_name)

def parse_current_ablum_page(soup, path):
    result_b = soup.find(class_="result_block")
    files_res = result_b.find_all(class_="sys_file_search_title")

    photo_from_album(files_res, path)

def album_url_rewrite(url):
    req_path = urlparse('?'.join(urlparse(url).path.split('&', maxsplit=1)))
    req_host = urlparse(url)

    req = req_path._replace(scheme=req_host.scheme)
    req = req._replace(netloc=req_host.netloc)
    req = req._replace(params=req_host.params)
    req = req._replace(query="per_page=2000")
    req = req._replace(fragment=req_host.fragment)

    return req.geturl()

def parse_the_album(url, path):
    page = urlopen(album_url_rewrite(url))
    soup = BeautifulSoup(page, 'html.parser')
    page_c1 = soup.find(id="page_column_1")
    the_title = page_c1.find(class_="dbTitle")

    parse_current_ablum_page(soup, path)

    multi_pages = soup.find(class_="pages_section")
    if multi_pages:
        multi_pages.find_all(class_="paginate_page")

class DolphinPhotoAlbum(Protocol)
    def __init__(self, deferred, save_path = "./Download"):
        self.deferred = deferred
        self.save_path = save_path 

    def dataReceived(self, bytes):
        soup = BeautifulSoup(bytes, 'html.parser')
        page_c1 = soup.find(id="page_column_1")
        the_title = page_c1.find(class_="dbTitle")

        parse_current_ablum_page(soup, path)

        multi_pages = soup.find(class_="pages_section")
        if multi_pages:
            multi_pages.find_all(class_="paginate_page")

class DolphinPhotoPage(Protocol)
    def __init__(self, deferred, save_path = "./Download"):
        self.deferred = deferred
        self.save_path = save_path 

    def dataReceived(self, bytes):
       soup = BeautifulSoup(bytes, 'html.parser')

       button = soup.find("button", class_="menuLink", title=the_raw_download_button)
       if button:
           photo_url = button.attrs['onclick']
           photo_url = re.findall("([^']*)'", photo_url)[1]
           print(photo_url)



def main():
    parse_the_album("https://www.insoler.com/m/photos/browse/album/15074893940142", "./")

if __name__ == "__main__":
    main();
