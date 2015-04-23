#!/usr/bin/env python
# -*- coding: iso-8859-5 -*-
import urllib
import urllib2
import cookielib
from urlparse import urlparse
from HTMLParser import HTMLParser
import json
import sys
import os

USERNAME = 'YOUR_USERNAME_TO_LOGIN' 
PASSWORD =  'YOUR_PASSWORD'

class FormParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.url = None
        self.params = {}
        self.in_form = False
        self.form_parsed = False
        self.method = "GET"

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "form":
            if self.form_parsed:
                raise RuntimeError("Second form on page")
            if self.in_form:
                raise RuntimeError("Already in form")
            self.in_form = True
        if not self.in_form:
            return
        attrs = dict((name.lower(), value) for name, value in attrs)
        if tag == "form":
            self.url = attrs["action"]
            if "method" in attrs:
                self.method = attrs["method"].upper()
        elif tag == "input" and "type" in attrs and "name" in attrs:
            if attrs["type"] in ["hidden", "text", "password"]:
                self.params[attrs["name"]] = attrs["value"] if "value" in attrs else ""

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "form":
            if not self.in_form:
                raise RuntimeError("Unexpected end of <form>")
            self.in_form = False
            self.form_parsed = True


def split_key_value(kv_pair):
    kv = kv_pair.split("=")
    return kv[0], kv[1]

    
def auth_user(email, password, client_id, scope, opener):
    response = opener.open(
        "http://oauth.vk.com/oauth/authorize?"
        "redirect_uri=http://oauth.vk.com/blank.html&response_type=token&"
        "client_id=%s&scope=%s&display=wap" % (client_id, ",".join(scope))
    )
    doc = response.read()
    parser = FormParser()
    parser.feed(doc)
    parser.close()
    if not parser.form_parsed or parser.url is None or "pass" not in parser.params or "email" not in parser.params:
        raise RuntimeError("Something wrong")
    parser.params["email"] = email
    parser.params["pass"] = password
    if parser.method == "POST":
        response = opener.open(parser.url, urllib.urlencode(parser.params))
    else:
        raise NotImplementedError("Method '%s'" % parser.method)
    return response.read(), response.geturl()

    
def give_access(doc, opener):
    parser = FormParser()
    parser.feed(doc)
    parser.close()
    if not parser.form_parsed or parser.url is None:
        raise RuntimeError("Something wrong")
    if parser.method == "POST":
        response = opener.open(parser.url, urllib.urlencode(parser.params))
    else:
        raise NotImplementedError("Method '%s'" % parser.method)
    return response.geturl()

    
def login_vk(opener):
    """
    Params:
        opener - urllib2 opener, that is going to be used during work with VK api
    Return:
        token that must be used when connecting to VK api
    """
    #Important connection info    
    client_id = '4434152'
    scope = ['friends', 'photos', 'audio']
    # redirect_uri=''   # to this url we'll receive code, that we will have to use later to get token
    # response_type='code'
    # v = '5.20'
    # lang = 'en'
    # test_mode=1
    email = USERNAME
    password = PASSWORD

    doc, url = auth_user(email, password, client_id, scope, opener)
    if urlparse(url).path != "/blank.html":
        # Need to give access to requested scope
        url = give_access(doc, opener)
    if urlparse(url).path != "/blank.html":
        print urlparse(url).path
        raise RuntimeError("Authenification failed")

    answer = dict(split_key_value(kv_pair) for kv_pair in urlparse(url).fragment.split("&"))
    if "access_token" not in answer or "user_id" not in answer:
        raise RuntimeError("Missing some values in answer")

    token = answer['access_token']
    return token


def userid_by_nickname(opener, token, nickname):
    response = opener.open('https://api.vk.com/method/users.search?q='+nickname+'&access_token='+token)
    uid = json.loads(response.read())['response'][1]['uid']
    if uid:
        return uid
    else:
        return


def music_of_user(opener, token, uid):
    url = 'https://api.vk.com/method/audio.get?owner_id='+str(uid)\
          + '&access_token=' + str(token) + '&need_user=1&count=10000'
    response_json = json.loads(opener.open(url).read())
    if 'error' in response_json:
        print 'Sorry, but I cannot retrieve music info for user ', uid, ':', response_json['error']["error_msg"],\
            'Code:', response_json['error']["error_code"]
        return
    music_list = response_json['response']
    return music_list


def download_audio_vk(audio):
    """
    download song from vk audio dictionary:
    {
      "aid": 296237419,
      "owner_id": 147267420,
      "artist": "Skillet",
      "title": "Never Surrender",
      "duration": 210,
      "url": "http:\/\/cs9-4v4.vk.me\/p14\/e7c3446470c603.mp3?extra=a519XSTKei9CYYhwKy432f7-su90o963hf1ZltuVUsmb",
      "lyrics_id": "2992371",
      "genre": 18
    }
    """
    try:
        filename = (audio['artist'] + u' - '
                    + audio['title']).strip().replace('/', '-').replace('"', ' ').replace(':', ' ') + '.mp3'
        u = urllib2.urlopen(audio['url'])
        file_size = int(u.info().getheaders("Content-Length")[0])
        try:
            print 'Downloading file ('+str(file_size/1024)+' KB)', filename.encode('cp1251'),
        except UnicodeEncodeError:
            print filename.encode('utf_8'),

        try:
            #first check if this file already exists.. and if yes - skip it
            if os.path.exists(filename):
                print " [SKIPPED]"
                return
            file_to_save = open(filename, 'wb')
        except IOError:
            try:
                filename = str(audio['aid']) + '.mp3'
                print " [*] renamed to " + filename,
                file_to_save = open(filename, 'wb')
            except IOError:
                print " [ERROR] Cannot create file!"
                return

        file_size_dl = 0
        block_sz = 8192
        while True:
            buff = u.read(block_sz)
            if not buff:
                break
            file_size_dl += len(buff)
            file_to_save.write(buff)
            status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
            status = status + chr(8)*(len(status)+1)
            print status,
        file_to_save.close()
        sys.stdout.flush()
    except urllib2.URLError, urlerr:
        print " [ERROR] Connection problem: " + str(urlerr)

    except Exception, err:
        print " [ERROR] Unexpected problem: " + str(err)

    print ""
    return


def download_all_audio_of_user_vk(opener, token, uid=0, nickname=None):
    if uid == 0 and not nickname:
        print "No user specified. I don't know whose audio to download"
        return
    real_id = uid
    if real_id == 0:
        real_id = userid_by_nickname(opener, token, nickname)
    if not real_id:
        print "Error while finding user id. No audio downloaded"
        return

    # get list of audio for user first
    music_list = music_of_user(opener, token, real_id)
    # 0 element here is number of songs, 1 element - user info, so lets clean this mess
    if not music_list:
        return
    user = music_list[1]
    songs_num = music_list[0]
    music_list = music_list[2:]  # now musicList has only music info
    print 'User', user['name'], '(id:', real_id, ') has', songs_num,\
        'songs in his/her VK playlist. We can get', len(music_list)
    yes = raw_input('Are you sure that you want to download all these songs right now? [yes/no]')
    if 'no' in yes:
        return
    
    for audio in music_list:
        download_audio_vk(audio)

    
def main():
    vkid = raw_input('Enter your VK profile ID (My settings -> Profile ID: ) ')
    uid = 0
    nick = None
    if vkid.isdigit():
        uid = int(vkid)
    else:
        nick = vkid

    opener = urllib2.build_opener(
        urllib2.HTTPCookieProcessor(cookielib.CookieJar()),
        urllib2.HTTPRedirectHandler())
    print 'Connecting to vk.com...'
    token = login_vk(opener)
    download_all_audio_of_user_vk(opener, token, uid=uid, nickname=nick)
    
    raw_input('Done!\nHave a nice day.\n(press Enter to exit)')
    

if __name__ == "__main__":
    main()
