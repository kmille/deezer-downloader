#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf8')


#coding:latin
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

import string

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


def enabletor():
    import socks
    import socket

    def create_connection(address, timeout=None, source_address=None):
        sock = socks.socksocket()
        sock.connect(address)
        return sock

    socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 9050)

    # patch the socket module
    socket.socket = socks.socksocket
    socket.create_connection = create_connection

    # todo: test if tor connection really works by connecting to https://check.torproject.org/

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


def find_re(txt, regex):
    """ Return either the first regex group, or the entire match """
    m = re.search(regex, txt)
    if not m:
        return
    gr = m.groups()
    if gr:
        return gr[0]
    return m.group()


def find_songs(obj):
    """ recurse into json object, yielding all objects which look like song descriptions """
    if type( obj ) == list:
        
        for item in obj:
            
            for tItem in find_songs(item):
                yield tItem
            #yield from find_songs(item)
            
    elif type( obj ) == dict:
        
        if "SNG_ID" in obj:
            yield obj
            
        for v in obj.values():
            
            for tItem in find_songs(v):
                yield tItem
            #yield from find_songs(v)


def parse_deezer_page(url):
    """
    extracts download host, and yields any songs found in a page.
    """
    data = deezer.session.get(url).text
    if not "MD5_ORIGIN" in data:
        print("We are not logged in")
        deezer.login()
        data = deezer.session.get(url).text

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



## Built-in namespace
#import __builtin__

## Extended dict
#class myDict(dict):
    
    #def s(self, key):
        #""" return value as UTF-8 String"""
        #if self:
            #return self.get(key).encode('utf-8')
        #else:
            #return ''

## Substitute the original str with the subclass on the built-in namespace    
#__builtin__.dict = myDict
##type bugfix
#dict = type( {} )

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


#http://stackoverflow.com/a/295242/3135511
# white list approach
#   Not really useful - for ex. throws out german umlaute: 
#      like дьц aus well aus acent letters йбъ
#      Attention this comment (with special letters) may trigger ask for how to encode this file when saving
#      I fixed this by specifing 
def FileNameClean_WL( FileName ):

    safechars = \
        '_-.() ' + \
        string.digits + \
        string.ascii_letters
    
    allchars  = string.maketrans('', '')

    outname = string.translate ( \
        FileName.encode('latin') ,
        allchars , 
        ''.join(
            set(allchars) - set(safechars)
            )
    )
    return outname
    
def FileNameClean( FileName ):
    return re.sub("[<>|?*]", "" ,FileName)	\
        .replace('/', ',') \
        .replace(':', '-') #\
        #.replace('"', "'") \
        #.replace('<', "" ) \
        #.replace('>', "" ) \
        #.replace('|', "" ) \
        #.replace('?', "" ) \
        #.replace('*', "" ) 




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
        
        print("Downloading song {}".format(outname.encode('utf-8')))
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
        print(url)
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



def printinfo(song):
    """ print info for a song """
    print "%9s %s %-5s %-30s %-30s %s" % (
        song["SNG_ID"], 
        song["MD5_ORIGIN"],
        song["MEDIA_VERSION"], 
        song["ART_NAME"], 
        song["ALB_TITLE"], 
        song["SNG_TITLE"]
    )


parser, args = (None, None)
def main():
    global parser, args, session

    import argparse
    parser = argparse.ArgumentParser(description='Deezer downloader')
    parser.add_argument('--tor', '-T', action='store_true', help='Download via tor')
    parser.add_argument('--list', '-l', action='store_true', help='Only list songs found on page')
    parser.add_argument('--overwrite', '-f', action='store_true', help='Overwrite existing downloads')
    parser.add_argument('urls', nargs='*', type=str)
    args = parser.parse_args()

    
    if args.tor:
        enabletor()

    if not args.urls:
        mainExC()

    for url in args.urls:
        for song in parse_deezer_page(url):
            if args.list:
                printinfo(song)
            else:
                #print "...", song
                try:
                    #raise Exception("Test Exception")
                    download(song)
                except Exception as e:
                    print e
                    traceback.print_exc()
                    if "FALLBACK" in song:
                        try:
                            print "trying fallback"
                            download(args, song["FALLBACK"])
                        except:
                            pass
                    #the download-track system is handled by the threading script


def scriptDownload(id, fname=None):
    global act_threads, completedSongs, totalSongs, args

    act_threads += 1
    progress(completedSongs * 100. / totalSongs, '  DL (total) > ')
    url = "https://www.deezer.com/track/%s" %id
    try:
        song = parse_deezer_page(url).next()
    except:
        print "        Could not find song; perhaps it isn't available here?"
        downloaded = True
        act_threads -= 1
        return downloaded
    #print "...", song)
    downloaded = False
    try:
        download(args, song, fname)
        downloaded = True
    except Exception as e:
        print e
        traceback.print_exc()
    if not downloaded and "FALLBACK" in song:
        try:
            print "trying fall back"
            download(args, song["FALLBACK"])
            downloaded = True
        except:
            pass
    print '    Done!' + ' '*(59-len('    Done!'))
    progress(completedSongs * 100. / totalSongs, '  DL (total) > ')
    completedSongs += 1
    act_threads -= 1
    return downloaded


init() #Start Colorama's init'

def get_link(link):
    for i in range(3):
        try:
            data = 'link=%s' %link
                #print json.dumps({'link':'https://www.deezer.com/track/126884459'})
                #print type(json.dumps({'link':'https://www.deezer.com/track/126884459'}))
            req = urllib2.Request('https://www.mp3fy.com/music/downloader.php')
            req.add_header("User-Agent", "Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11")
            response = urllib2.urlopen(req, data)
            #print result)
            retDict = json.loads(response.read())
            try:
                return retDict['dlink']
            except KeyError:
                return False
        except ValueError:
            print 'Okay... that\'s weird. Wait a momento...'

def load_songs():
    'Generate a list of songs from a playlist csv file.'

    while True:
        res = raw_input('Choose a mode - \n'
                        '(0) playlist (Song CSV)\n'
                        '(1) playlist (Deezer link)\n'
                        '(2) title   or\n'
                        '(3) iTunes %i Top Charts ? > ' % config_topsongs_limit)
        try:
            if int(res) in (0, 1, 2, 3):
                break
            else: continue
        except:
            continue
    if int(res) == 0:
        print '''WARNING!
Using the CSV playlist function can be inaccurate and cumbersome. Also, if you don't have bs4 it will crash.'
Try using the Deezer playlist instead!'''
        try:
            #file_path = 'playlist.csv' # FOR EXPERIMENTAL PURPOSES, PLEASE REMOVE
            file_path = sys.argv[1]   # FOR EXPERIMENTAL PURPOSES, PLEASE UNCOMMENT
        except IndexError:
            print 'You need to choose a .csv file to use. If you don\'t have one, '\
                  'get one from <http://joellehman.com/playlist/>!'
            root = __import__('Tkinter').Tk()
            root.withdraw()
            root.update()
            file_path = openfile(title='Choose a .csv file')
            print file_path

        try:                            
            mFile = open(file_path, 'r')
            sPlaylist = csv.reader(mFile)
            return sPlaylist, False
        except IOError:
            return 'NoFile'
    elif int(res) == 1:
        deezerLink = raw_input('What\'s the link/ID to the Deezer playlist? > ')
        deezerAPILink = 'https://api.deezer.com/playlist/%s' %deezerLink.split('/')[-1]
            #print deezerAPILink
            #link_data_json = urllib2.urlopen(deezerAPILink).read()
        try:
            link_data_json = urllib2.urlopen(deezerAPILink).read()
        except:
            print 'Oops! Did something go wrong? Check your link...'
            sys.exit('FAIL')

        #print link_data_json
        link_data = json.loads(link_data_json)
        if 'error' in link_data:
            print 'Something went wrong. Check your link...'
            sys.exit('FAIL')
        #print link_data
        #print link_data['tracks']['data']
        sPlaylist = []
        for trackData in link_data['tracks']['data']:
            sPlaylist.append((trackData['title'],
                              trackData['artist']['name'],
                              trackData['link']))

        #Print sPlaylist
        return ['JUNK'] + sPlaylist, True

    elif int(res) == 2:
        search = raw_input('Search? > ')
        return deezerSearch(search)
        # return ('JUNK_DISCARD',(song_name, track))

    else:
        iTunesText = ('iTunes country code for your country?\n'
                      '(AU) for Australia\n'
                      '(US) for the United States\n'
                      '(GB) for Great Britain) > ')

        if sys.version_info[0] == 2:
            countryCode = raw_input(iTunesText)
        else:
            countryCode =     input(iTunesText)

        countryCode = countryCode.lower()
        feedlink = "http://itunes.apple.com/%s/rss/topsongs/limit=%i/explicit=true/xml" % \
            (countryCode, config_topsongs_limit)
        feed = feedparser.parse(feedlink)
        if feed["bozo"]:
            input("Not a valid country code.")
            sys.exit()

        songslist = []
        for item in feed["items"]:
            title = unicodedata.normalize('NFKD', u"%s" %(item["title"])) \
                .encode('ascii', 'ignore')
            #print title					
            title  = "".join ( title         .split(" - ")[:-1] )
            artist =           item["title"] .split(" - ")[ -1]

#I Feel It Coming (feat. Daft Punk) - The Weeknd
#I Feel It Coming

#I Dont Wanna Live Forever (Fifty Shades Darker) - ZAYN & Taylor Swift
#I Dont Wanna Live Forever (Fi
#I Don\u2019t Wann...
            phrases = ("feat\.", "ft\.")
            modifiers = (
                (r"\("	, r"\)"	), 
                ( ""	,  ""	), 
                ( " "	,  ""	), 
                ( " "	,  " "	)
            )
            for ph in phrases:
                for mod in modifiers:
                    title = re.sub( mod[0] + ph + ".+" + mod[1], "", title)

            print title	
            title = title.strip()

            songslist.append( [title, artist] )
        return ["JUNK"] + songslist, False

def download_songs(sPlaylist, url=False):
    'Download songs, using the Deezer search engine.'
    global completedSongs, totalSongs, act_threads

    currentSong = 1
    green = Fore.GREEN
    black = Back.BLACK
    userOpin = raw_input('Do you want to number the songs? [Y/N]')
    userOpin = userOpin.lower().startswith('y')
    print Fore.RED + "Downloading to '" + config_DL_Dir + "'"
    print green + 'Starting download with Deezer'
    first = True
    second = False
    completedSongs = 0
    totalSongs = len(sPlaylist)-1
    startProgress('  DL (total) > ')
    unchUrl = copy.deepcopy(url)
        #progress(file_size_dl * 100. / file_size_int, '  DL (total) > ')
        #endProgress('  DL (done!)> ')
    for song in sPlaylist:
        while act_threads > 4:
            time.sleep(0.5)
        if first:
            first = False
            second = True
            continue
        if second:
            second = False

        print green + '    Song: %s' %song[0] + ' '*(59-len('    Song: %s' %song[0]))
        progress( completedSongs * 100. / totalSongs, '  DL (total) > ')

        if userOpin:
            sTitle = '%s. %s' %(currentSong, song[0]) 
        else: 
            sTitle = song[0]

        file_name = 'downloads/%s - %s.mp3' %(
            sTitle.rstrip(), 
            song[1].rstrip()
        )

        file_name = file_name.rstrip()
        if os.path.exists(file_name):
            print '      Exists already. Skipping...' + ' '*(59-\
                                                             len  ('      Exists already. Skipping...'))
            progress(completedSongs * 100. / totalSongs, '  DL (total) > ')
            currentSong += 1
            continue

        if not unchUrl:

            songTitle  = song[0]
            artistName = song[1]

            url = 'https://api.deezer.com/search?q=%s%%20%s' %(
                MakeUrlItem( songTitle),
                MakeUrlItem(artistName) )

            html_mpfy = urllib2.urlopen( url ).read()
            js = json.loads(html_mpfy)
            try:
                downloadLink = js["data"][0]["id"]
                #scriptDownload(downloadId, file_name)
                if userOpin:
                    dw_thr = threading.Thread(target=scriptDownload, args=(downloadLink, file_name))
                else:
                    dw_thr = threading.Thread(target=scriptDownload, args=(downloadLink, ))
                dw_thr.start()

            except IndexError:
                print url		

                print green + '      Song not found. Skipping...' + ' '*(59-len('      Song not found. Skipping...'))
                progress(completedSongs * 100. / totalSongs, '  DL (total) > ')
        else:
            try:
                link = re.findall(r"track/(\d*)", song[2])[0]
            except IndexError:
                link = ""
            if link:
                dw_thr = threading.Thread(target=scriptDownload, args=(link, ))
                #download_file(link, sTitle, song[1])
                dw_thr.start()
            else:
                print '    Skipping... (Could not download)' + \
                      ' '*(59-len('    Skipping... (Could not download)'))
                progress(completedSongs * 100. / totalSongs, '  DL (total) > ')
        currentSong += 1
        progress(completedSongs * 100. / totalSongs, '  DL (total) > ')
    while True:
        if act_threads == 1:
            break
        time.sleep(0.5)
    endProgress('  DL (done!)> ')

def startProgress(title):
    to_write = title + ": [" + "-"*40 + "]"
    sys.stdout.write(to_write + chr(8)*len(to_write))
    sys.stdout.flush()

def progress(x, title):
    x_t = int(x * 40 // 100)
    to_write = title + ": [" + "#"*x_t + "-"*(40-x_t) + "]"
        #sys.stdout.write("#" * (x - progress_x))
    sys.stdout.write(to_write + chr(8)*len(to_write))
    sys.stdout.flush()

def endProgress(title):
    to_write = title + ": [" + "#"*40 + "]\n"
    sys.stdout.write(to_write)
    sys.stdout.flush()

def MakeUrlItem(item):
    try:
        return '+'.join(urllib.quote_plus(item).split(' '))
    except:
        return ''

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
    




    'Searches for a song using the Deezer API.'

    """
    query = 'https://api.deezer.com/search?q=%s' %  \
        ( MakeUrlItem( search))
    #print query
    qResultRaw = urllib2.urlopen(
        query).read()
    cnt = 1
    """

    #print qResultRaw
    try:
        qResult = json.loads(qResultRaw)['data']
        return qResult
    except ValueError:
        print 'Things went wrong. There was NOTHING returned for your search! :O'
        return None

    cnt = 0
    group = 0
    print Fore.RESET + 'Press the KEY to select, or any other to continue'
    print Fore.RED + Back.WHITE + 'KEY:\tTRACK - ARTIST'
    for i in qResult:
        try:
            if group and group*5 + cnt >= len(qResult):
                print Fore.RESET + 'Looks like the end! Sorry...'
            if not group:
                print Fore.RED + Back.WHITE + '%s:\t%s - %s' %(cnt+1, qResult[cnt]['title'], qResult[cnt]['artist']['name'])
            else:
                print Fore.RED + Back.WHITE + '%s:\t%s - %s' %(cnt+1, qResult[(group*5-1) + cnt]['title'], qResult[(group*5-1) + cnt]['artist']['name'])
        except:
            print Fore.RESET + 'Error'

        if cnt >= 4 or group*5 + cnt + 1 == len(qResult): # NEED TO FINISH
            #print range(1, cnt+2)
            q = raw_input(Fore.RESET + Back.RESET + '  Which song? ')
            if q in [str(x) for x in range(1, cnt+2)]:
                cnNum = int(q)-1
                if not group:
                    qr = qResult[cnNum]
                    #userOpin = raw_input(Fore.RESET + '  Chosen: %s by %s. Confirm? ' %(qr['title'], qResult[cnNum]['artist']['name']))
                    if True: #userOpin.lower().startswith('y'):
                        result = previewSong(qr)
                        if result:
                            print "NOTE: Due to the nature of the script, the progress bar will not move until the whole song is finished downloading (it's made for downloading with a playist.)"
                            return ['JUNK',[qr['title'], 
                                            qr['artist']['name'], 
                                            qr['link']]], True
                else:
                    qr = qResult[(group*5-1)+cnNum]
                    #userOpin = raw_input('  Chosen: %s by %s. Confirm? ' %(\
                    #    qr['title'], 
                    #    qr['artist']['name']))
                    if True:#userOpin.lower().startswith('y'):
                        result = previewSong(qr)
                        if result:
                            print "NOTE: Due to the nature of the script, the progress bar will not move until the whole song is finished downloading (it's made for downloading with a playist.)"
                            return ['JUNK',[qr['title'], 
                                            qr['artist']['name'], 
                                            qr['link']]], True
            print Fore.RESET + 'Press the KEY to select, or any other to continue'
            print Fore.RED + 'KEY:\tTRACK - ARTIST'
            group += 1
            cnt = -1
        cnt += 1
    print 'Looks like the end...'
    sys.exit('FAIL')

def previewSong(qPlaylist):
    'Creates a preview of the song'

    urllib.urlretrieve(qPlaylist['preview'], 'temp.mp3')
    #with open('temp.mp3','w') as tempMedia:
        #content = urllib2.urlopen(qPlaylist['preview']).read()
        #print qPlaylist['preview']
        #tempMedia.write(content)

    player = pyglet.media.Player()
    player.queue(pyglet.media.load('temp.mp3'))
    player.play()
    userOpin = raw_input('  Are you sure you want to choose this song? ')
    player.pause()
    del player
    if userOpin.lower().startswith('y'):
        return True

def mainExC():
    'Run the program as an executable'
    global act_threads
    sPlaylist, oldSearch = load_songs()
    if sPlaylist:
        download_songs(sPlaylist, oldSearch)
        return 'SUCCESS'
    else:
        return 'FAIL'

act_threads = 1
completedSongs = 0
totalSongs = 0

import re
def sorted_nicely( l ):
    """ Sorts the given iterable in the way that is expected.
 
    Required arguments:
    l -- The iterable to be sorted.
 
    """
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key = alphanum_key)


import mpd

def mpd_update(songs, add_to_playlist):
        print("Updating mpd")
	c = mpd.MPDClient(use_unicode=True)
	c.connect("localhost", 6600)
	c.update()
	if add_to_playlist:
            for song in songs:
		print("Adding {}".format(song))
	        c.add(song)

#songs = [ "deezer/Die Toten Hosen - Wannsee.mp3" ]
#mpd_update(songs, True)

def my_search():
    results = deezerSearch("coldplay", 'track')
    for item in results:
        print("   ".join(item.values()))
    results = deezerSearch("greatest hits", 'album')
    for item in results:
        print("   ".join(item.values()))

def my_list_album(album_id):
    print("doing my_list_album")
    url = "https://www.deezer.com/de/album/{}".format(album_id)
    songs = list(parse_deezer_page(url))
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
            #print("Adding", s)
    return nice

def my_download_playlist(playlist_id):
    url = "https://www.deezer.com/de/playlist/{}".format(playlist_id)
    hans =  list(parse_deezer_page(url))
    for i,song in enumerate(parse_deezer_page(url)):
        #print("Downloading {} {}".format(i, song['SNG_TITLE']))
        #set_trace()
        download(song, False)

def my_download_from_json_file():
    import json
    songs = json.load(open("/tmp/songs.json"))
    for song in songs['results']['SONGS']['data']:
        print("Downloading {}".format(song['SNG_TITLE']))
        download(song)


def my_download_album(album_id, update_mpd, add_to_playlist):
    url = "https://www.deezer.com/de/album/{}".format(album_id)
    song_locations = []
    for song in parse_deezer_page(url):
        song_locations.append(download(song, album=True))
    if update_mpd:
        mpd_update(set(song_locations), add_to_playlist)
    return sorted_nicely(set(song_locations))

def my_download_song(track_id, update_mpd, add_to_playlist):
    url = "https://www.deezer.com/de/track/{}".format(track_id)
    song = list(parse_deezer_page(url))[0]
    print("Downloading song {}".format(track_id))
    song_location = download(song, album=False)
    if update_mpd:
        mpd_update([song_location], add_to_playlist)


if __name__ == '__main__':
    pass
    my_download_song("917265", False, False)
    my_download_album("72251042", False, False)
    my_download_playlist("5434472702")
