#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf8')

from ipdb import set_trace
from deezer_login import DeezerLogin
from os.path import basename

import arrow
import requests
from settings import download_dir, music_dir
deezer = DeezerLogin()
"""
  Author:   --<>
  Purpose: 
     Download and decrypt songs from deezer.
     The song is saved as a mp3.
     
     No ID3 tags are added to the file.
     The filename contains album, artist, song title.
     
     Usage:
     
     python DeezerDownload.py http://www.deezer.com/album/6671241/
     python DeezerDownload.py
     
     This will create mp3's in the '\downloads' directory, with the song information in the filenames.
  Created: 16.02.2017

"""

config_DL_Dir 			= download_dir
config_topsongs_limit	= 50

import sys
from Crypto.Hash import MD5
from Crypto.Cipher import AES, Blowfish
import re
import os
import json
import struct
import urllib
import urllib2
import HTMLParser
import copy
import traceback
import csv
import threading
import time
import httplib
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error
from decimal import Decimal
from colorama import Fore, Back, Style, init
#from tkFileDialog import askopenfilename as openfile
import pyglet
import feedparser
import unicodedata
from binascii import a2b_hex, b2a_hex
import json

import string
import re
import mpd

#load AVBin
try:
    #pyglet.lib.load_library('avbin')
    pass
except Exception as e:
    print 'Trying to load avbin64...'
    pyglet.lib.load_library('avbin64')
    print 'Success!'


pyglet.have_avbin=True

# global variable
host_stream_cdn = "https://e-cdns-proxy-%s.dzcdn.net/mobile/1"
setting_domain_img = "https://e-cdns-images.dzcdn.net/images"



class ScriptExtractor(HTMLParser.HTMLParser):
    """ extract <script> tag contents from a html page """
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.scripts = []
        self.curtag = None

    def handle_starttag(self, tag, attrs):
        self.curtag = tag.lower()

    def handle_data(self, data):
        if self.curtag == "script":
            self.scripts.append(data)

    def handle_endtag(self, tag):
        self.curtag = None


def FileNameClean( FileName ):
    return re.sub("[<>|?*]", "" ,FileName)     \
        .replace('/', ',') \
        .replace(':', '-') #\
        #.replace('"', "'") \
        #.replace('<', "" ) \
        #.replace('>', "" ) \
        #.replace('|', "" ) \
        #.replace('?', "" ) \
        #.replace('*', "" )




def find_re(txt, regex):
    """ Return either the first regex group, or the entire match """
    m = re.search(regex, txt)
    if not m:
        return
    gr = m.groups()
    if gr:
        return gr[0]
    return m.group()


def parse_deezer_page(search_type, id):
    """
    extracts download host, and yields any songs found in a page.
    """
    url = "https://www.deezer.com/de/{}/{}".format(search_type, id)
    data = deezer.session.get(url).text
    if not "MD5_ORIGIN" in data:
        raise Exception("We are not logged in.")

    parser = ScriptExtractor()
    parser.feed(data.encode('utf-8'))
    parser.close()

    # note: keeping track of songs by songid, this might still lead to duplicate downloads,
    # for instance when the same song is present on multiple albums.
    # if you want to avoid that, add the MD5_ORIGIN to the foundsongs set, instead of the SNG_ID.
    foundsongs = set()
    for script in parser.scripts:
        
        jsondata = find_re(script, r'{"DATA":.*')
        if jsondata:
            DZR_APP_STATE = json.loads( jsondata )
            if DZR_APP_STATE['DATA']['__TYPE__'] == 'playlist' or DZR_APP_STATE['DATA']['__TYPE__'] == 'album':
                for song in DZR_APP_STATE['SONGS']['data']:
                    yield song
            elif DZR_APP_STATE['DATA']['__TYPE__'] == 'song':
                    yield DZR_APP_STATE['DATA']



def md5hex(data):
    """ return hex string of md5 of the given string """
    h = MD5.new()
    h.update( data) 
    return b2a_hex( h.digest() )


def hexaescrypt(data, key):
    """ returns hex string of aes encrypted data """
    c = AES.new( key, AES.MODE_ECB)
    return b2a_hex( c.encrypt(data) )


def genurlkey( songid, md5origin, mediaver=4, fmt=1):
    """ Calculate the deezer download url given the songid, origin and media+format """
    data = '\xa4'.join(_.encode("utf-8") for _ in [
        md5origin, 
        str( fmt ), 
        str( songid ), 
        str( mediaver )
    ])
    
    data = '\xa4'.join( [ md5hex(data), data ] ) + '\xa4'
    
    if len(data)%16:
        data += b'\0' * (16-len(data)%16)
        
    return hexaescrypt(data, "jo6aey6haid2Teih" ).decode('utf-8')


def calcbfkey(songid):
    """ Calculate the Blowfish decrypt key for a given songid """
    h = md5hex( "%d" % songid)
    key = "g4el58wc0zvf9na1"
    
    return "".join(
        chr( 
            ord( h[ i ]     ) ^ 
            ord( h[ i + 16] ) ^ 
            ord( key[i]     )
            ) for i in range( 16 )
    )


def blowfishDecrypt(data, key):
    """ CBC decrypt data with key """
    c = Blowfish.new( key , 
                      Blowfish.MODE_CBC, 
                      a2b_hex( "0001020304050607" )
                      )
    return c.decrypt(data)


def decryptfile(fh, key, fo):
    """
    Decrypt data from file <fh>, and write to file <fo>.
    decrypt using blowfish with <key>.
    Only every third 2048 byte block is encrypted.
    """
    blockSize = 0x800 #2048 byte
    i = 0
    
    #while True:
    for data in fh.iter_content(blockSize):
        #data = fh.read( blockSize )
        if not data:
            break

        isEncrypted  = ( (i % 3) == 0 )
        isWholeBlock = len(data) == blockSize
        
        if isEncrypted and isWholeBlock:
            data = blowfishDecrypt(data, key)
            
        fo.write(data)
        i += 1


def getformat(song):
    """ return format id for a song """
    #return 8 if song.get("FILESIZE_FLAC") else \
    return 3 if song.get("FILESIZE_MP3_320") else \
           5 if song.get("FILESIZE_MP3_256") else \
           1
#FILESIZE_MP3_128 FILESIZE_MP3_64 FILESIZE_AAC_64


def writeid3v1_1(fo, song):
    
    # Bugfix changed song["SNG_TITLE... to song.get("SNG_TITLE... to avoid 'key-error' in case the key does not exist
    def song_get(song, key):
        try:
            return song.get(key).encode('utf-8')
        except Exception as e:
            return ""
        
    def album_get(key):
        global album_Data
        try:
            return album_Data.get(key).encode('utf-8')
        except Exception as e:
            return ""    
            
    data = struct.pack("3s" "30s" "30s" "30s" "4s" "28sB" "B"  "B", 
                       "TAG",                                             # header
                       song_get (song, "SNG_TITLE"),                             # title
                       song_get (song, "ART_NAME") ,                             # artist
                       song_get (song, "ALB_TITLE"),                             # album
                       album_get("PHYSICAL_RELEASE_DATE"),                # year
                       album_get("LABEL_NAME"), 0,                        # comment
                       
                       int(song_get(song, "TRACK_NUMBER") or 0),                # tracknum
                       255                                                # genre
                    )
    fo.write( data )

def downloadpicture(id):
    try:        
       
        fh = urllib2.urlopen(
            setting_domain_img + "/cover/" + id + "/1200x1200.jpg"
        )
        return fh.read()
    
    except Exception as e:
        print "no pic", e
    

def writeid3v2(fo, song):
    
    def make28bit(x):
        return  (
            (x<<3) & 0x7F000000) | (
            (x<<2) &   0x7F0000) | (
            (x<<1) &     0x7F00) | \
            (x     &       0x7F)
    
    def maketag(tag, content):
        return struct.pack( ">4sLH", 
                             tag.encode( "ascii" ), 
                             len(content), 
                             0
                           ) + content

    def album_get(key):
        global album_Data
        try:
            return album_Data.get(key)#.encode('utf-8')
        except Exception as e:
            return ""  
        
    def song_get(song, key):
        try:
            return song[key]#.encode('utf-8')
        except Exception as e:
            return ""    
    
    def makeutf8(txt):
        return b"\x03" +  txt .encode('utf-8') 
    
    def makepic(data):
        # Picture type:
        # 0x00     Other
        # 0x01     32x32 pixels 'file icon' (PNG only)
        # 0x02     Other file icon
        # 0x03     Cover (front)
        # 0x04     Cover (back)
        # 0x05     Leaflet page
        # 0x06     Media (e.g. lable side of CD)
        # 0x07     Lead artist/lead performer/soloist
        # 0x08     Artist/performer
        # 0x09     Conductor
        # 0x0A     Band/Orchestra
        # 0x0B     Composer
        # 0x0C     Lyricist/text writer
        # 0x0D     Recording Location
        # 0x0E     During recording
        # 0x0F     During performance
        # 0x10     Movie/video screen capture
        # 0x11     A bright coloured fish
        # 0x12     Illustration
        # 0x13     Band/artist logotype
        # 0x14     Publisher/Studio logotype        
        imgframe = ( "\x00",                 # text encoding
                     "image/jpeg",  "\0",    # mime type
                     "\x03",                 # picture type: 'Cover (front)'
                     ""[:64],  "\0",         # description
                     data
                    )
        
        return b'' .join( imgframe )
 
    
    # get Data as DDMM
    try:
        phyDate_YYYYMMDD = album_get("PHYSICAL_RELEASE_DATE") .split('-') #'2008-11-21'
        phyDate_DDMM    = phyDate_YYYYMMDD[2] + phyDate_YYYYMMDD[1]
    except:
        phyDate_DDMM    = ''
    
    # get size of first item in the list that is not 0
    try:
        FileSize = [ 
            song_get(song,i) 
            for i in (
                'FILESIZE_AAC_64',
                'FILESIZE_MP3_320',
                'FILESIZE_MP3_256',
                'FILESIZE_MP3_64',
                'FILESIZE',
                ) if song_get(song,i)
            ][0]
    except:
        FileSize    = 0
    
    try:
        track = "%02s" % song["TRACK_NUMBER"]
        track += "/%02s" % album_get("TRACKS")
    except:
        pass
    
    # http://id3.org/id3v2.3.0#Attached_picture
    id3 = [ 
        maketag( "TRCK", makeutf8( track    ) ),     # The 'Track number/Position in set' frame is a numeric string containing the order number of the audio-file on its original recording. This may be extended with a "/" character and a numeric string containing the total numer of tracks/elements on the original recording. E.g. "4/9".
        maketag( "TLEN", makeutf8( str( int(song["DURATION"]) * 1000 )          ) ),     # The 'Length' frame contains the length of the audiofile in milliseconds, represented as a numeric string.
        maketag( "TORY", makeutf8( str( album_get("PHYSICAL_RELEASE_DATE")[:4] )) ),     # The 'Original release year' frame is intended for the year when the original recording was released. if for example the music in the file should be a cover of a previously released song 
        maketag( "TYER", makeutf8( str( album_get("DIGITAL_RELEASE_DATE" )[:4] )) ),     # The 'Year' frame is a numeric string with a year of the recording. This frames is always four characters long (until the year 10000).
        maketag( "TDAT", makeutf8( str( phyDate_DDMM                           )) ),     # The 'Date' frame is a numeric string in the DDMM format containing the date for the recording. This field is always four characters long.
        maketag( "TPUB", makeutf8( album_get("LABEL_NAME")                ) ),     # The 'Publisher' frame simply contains the name of the label or publisher.
        maketag( "TSIZ", makeutf8( str( FileSize                               )) ),     # The 'Size' frame contains the size of the audiofile in bytes, excluding the ID3v2 tag, represented as a numeric string.
        maketag( "TFLT", makeutf8( "MPG/3"                                ) ),
        
        ]  # decimal, no term NUL
    id3.extend( [
        maketag( ID_id3_frame, makeutf8( song_get(song, ID_song ))  ) for (ID_id3_frame, ID_song) in \
        (
            ( "TALB", "ALB_TITLE"   ),   # The 'Album/Movie/Show title' frame is intended for the title of the recording(/source of sound) which the audio in the file is taken from.
            ( "TPE1", "ART_NAME"    ),   # The 'Lead artist(s)/Lead performer(s)/Soloist(s)/Performing group' is used for the main artist(s). They are seperated with the "/" character.
            ( "TPE2", "ART_NAME"    ),   # The 'Band/Orchestra/Accompaniment' frame is used for additional information about the performers in the recording.
            ( "TPOS", "DISK_NUMBER" ),   # The 'Part of a set' frame is a numeric string that describes which part of a set the audio came from. This frame is used if the source described in the "TALB" frame is divided into several mediums, e.g. a double CD. The value may be extended with a "/" character and a numeric string containing the total number of parts in the set. E.g. "1/2".
            ( "TIT2", "SNG_TITLE"   ),   # The 'Title/Songname/Content description' frame is the actual name of the piece (e.g. "Adagio", "Hurricane Donna").
            ( "TSRC", "ISRC"        ),   # The 'ISRC' frame should contain the International Standard Recording Code (ISRC) (12 characters).
        )
    ])

    #try:
        #id3.append(
            #maketag( "APIC", makepic(
                        #downloadpicture( song["ALB_PICTURE"] )
                    #)
            #)
        #)
    #except Exception as e:
        #print "no pic", e

    id3data = b"".join(id3)
#>	big-endian
#s	char[]	bytes
#H	unsigned short	integer	2
#B	unsigned char	integer	1
#L	unsigned long	integer	4


    hdr = struct.pack(">" 
                      "3s" "H" "B" "L", 
                      "ID3".encode("ascii"),
                      0x300,   # version
                      0x00,    # flags
                      make28bit( len( id3data) ) )

    fo.write(hdr)
    fo.write(id3data)



def download(song, album, fname="", ):
    """ download and save a song to a local file, given the json dict describing the song """

    if not song.get("SNG_ID"):
        print("Invalid song")
        return

    urlkey = genurlkey( int(song.get("SNG_ID")), 
                        str(song.get("MD5_ORIGIN")), 
                        int(song.get("MEDIA_VERSION")), 
                        getformat( song )
                        )
    key = calcbfkey( int(song["SNG_ID"]) )

    tracknum = ("%02i" % int(song["TRACK_NUMBER"])) \
                 if "TRACK_NUMBER" in song \
                 else ""

    for i in ("ART_NAME", "ALB_TITLE", "SNG_TITLE", "SNG_ID"):
        try:
            exec("%s = str(song[\"%s\"])" %(i, i))
        except UnicodeEncodeError:
            exec("%s = song[\"%s\"]" %(i, i))
    
    if not fname:
        if album:
            album_dir = "{} - {}".format(song['ART_NAME'], song['ALB_TITLE'])
            outname = album_dir + "/" + FileNameClean ("%s - %s - %s.mp3" % (song['TRACK_NUMBER'], ART_NAME, SNG_TITLE))
        else:
            outname = FileNameClean ("%s - %s.mp3" % (ART_NAME, SNG_TITLE))
            album_dir = ""
        
      # Make DL dir
        try: 
            #print("Creating dir", (config_DL_Dir + "/" + album_dir))
            os.makedirs( config_DL_Dir + "/" + album_dir )
        except Exception as e:
            #print(e)
            pass
        
        print("Downloading song '{}'".format(outname.encode('utf-8')))
        f = outname
        outname = config_DL_Dir + "/%s" %outname
    else:
        outname = fname

    # wont work with time stamp in filename...
    if os.path.exists(os.path.join(config_DL_Dir, outname)):
        print("File {} already there. skipping".format(basename(outname)))
        return os.path.join(download_dir[len(music_dir) + 1 :] ,f)

    try:
        url = (host_stream_cdn + "/%s") % (str( song["MD5_ORIGIN"] )[0],urlkey )
        # print(url)
        fh  = deezer.session.get(url)

        with open(outname, "w+b") as fo:
          # add songcover and DL first 30 sec's that are unencrypted             
            writeid3v2 ( fo, song)
            decryptfile( fh, key, fo)
            writeid3v1_1 ( fo, song)
            
        ##############################################
        toWS = MP3( outname , ID3 = ID3)
        
        try: 
            toWS.add_tags()
        except: pass
    
        toWS.tags.add(
            APIC(
                encoding = 3,        # 3 is for utf-8
                mime = 'image/jpeg', # image/jpeg or image/png
                type = 3,            # 3 is for the cover image
                desc = u'Cover',
                data = downloadpicture( song["ALB_PICTURE"] )
            )
        )
        toWS.save( v2_version = 3 )
            

    except IOError as e:
        print "IO_ERROR: %s" % (e)
        raise        
        
    except Exception as e:
        print "ERROR downloading from %s: %s" % (host_stream_cdn, e)
        #raise
    else:
        print("Dowload finished. Dest: {}".format(outname))
    return os.path.join(download_dir[len(music_dir) + 1 :] ,f) # (deezer download dir - download dir) + file name of the downloaded file


init() #Start Colorama's init'


def deezerSearch(search, type):
    search = search.encode('utf-8')
    search = urllib.quote_plus(search)
    resp = requests.get("https://api.deezer.com/search/{}?q={}".format(type,  search))
    return_nice = []
    for item in resp.json()['data'][:10]:
        i = {}
        i['id'] = str(item['id'])
        if type == "album":
            #set_trace()
            i['album'] = item['title']
            i['artist'] = item['artist']['name']
            i['title'] = ''
        if type == "track":
            i['title'] = item['title']
            i['album'] = item['album']['title']
            i['artist'] = item['artist']['name']
        return_nice.append(i)
    return return_nice
    


def sorted_nicely( l ):
    """ Sorts the given iterable in the way that is expected.
 
    Required arguments:
    l -- The iterable to be sorted.
 
    """
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    l = [x for x in l if x]
    return sorted(l, key = alphanum_key)



def mpd_update(songs, add_to_playlist):
        print("Updating mpd")
	c = mpd.MPDClient(use_unicode=True)
	c.connect("localhost", 6600)
	c.update()
	if add_to_playlist:
            songs = [s for s in songs if s]
            while len(c.search("file", songs[0])) == 0:
                # c.update() does not block wait for it 
                print("'{}' not found in the music db. Let's wait a second for it".format(songs[0]))
                time.sleep(1)
            for song in songs:
                if song:
                    print("Adding '{}' to mpd playlist".format(song))
                    c.add(song)


def my_list_album(album_id):
    songs = list(parse_deezer_page("album", album_id))
    print("Got {} songs for album {}".format(len(songs), album_id))
    nice = []
    for song in songs:
        if "SNG_ID" in song.keys():
            s = {}
            s['id'] = str(song["SNG_ID"])
            s['artist'] = song["ART_NAME"]
            s['album'] = song["ALB_TITLE"]
            s['title'] = song["SNG_TITLE"]
            nice.append(s)
    return nice


def my_download_from_json_file():
    songs = json.load(open("/tmp/songs.json"))
    for song in songs['results']['SONGS']['data']:
        print("Downloading {}".format(song['SNG_TITLE']))
        download(song)


def my_download_album(album_id, update_mpd, add_to_playlist):
    song_locations = []
    for song in parse_deezer_page("album", album_id):
        song_locations.append(download(song, album=True))
    songs_locations = sorted_nicely(set(song_locations))
    if update_mpd:
        mpd_update(song_locations, add_to_playlist)
    return song_locations


def my_download_song(track_id, update_mpd=True, add_to_playlist=False):
    song = list(parse_deezer_page("track", track_id))[0]
    song_location = download(song, album=False)
    if update_mpd:
        mpd_update([song_location], add_to_playlist)


if __name__ == '__main__':
    my_download_song("2271563", True, True)
    my_download_album("93769922", create_zip=True)
    pass
