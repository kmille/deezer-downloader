#!/usr/bin/env python3

from ipdb import set_trace
from deezer_login import DeezerLogin
from os.path import basename

from settings import (deezer_download_dir_songs, deezer_download_dir_albums, use_mpd, mpd_host, mpd_port, mpd_music_dir_root,
                      download_dir_zips, download_dir_playlists, youtubedl_download_dir)
deezer = DeezerLogin()

from Crypto.Hash import MD5
from Crypto.Cipher import AES, Blowfish
import re
import os
import json
import struct
#import urllib
import urllib.parse
import html.parser
import time
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error
from binascii import a2b_hex, b2a_hex

import mpd
from zipfile import ZipFile, ZIP_DEFLATED

from youtube import youtubedl_download, YoutubeDLFailedException, DownloadedFileNotFoundException
from spotify import get_songs_from_spotify_website


# BEGIN TYPES
TYPE_TRACK = "track"
TYPE_ALBUM = "album"
TYPE_PLAYLIST = "playlist"
# END TYPES


def check_download_dirs_exist():
    for directory in [deezer_download_dir_songs, download_dir_zips,
                      download_dir_playlists, youtubedl_download_dir]:
        os.makedirs(directory, exist_ok=True)


check_download_dirs_exist()


class ScriptExtractor(html.parser.HTMLParser):
    """ extract <script> tag contents from a html page """
    def __init__(self):
        html.parser.HTMLParser.__init__(self)
        self.scripts = []
        self.curtag = None

    def handle_starttag(self, tag, attrs):
        self.curtag = tag.lower()

    def handle_data(self, data):
        if self.curtag == "script":
            self.scripts.append(data)

    def handle_endtag(self, tag):
        self.curtag = None


def FileNameClean(FileName):
    print("TODO: fix FileNameClean")
    return FileName
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
    #print("TODO: find_re -> Das muss schöner gehen")
    #print(regex)
    m = re.search(regex, txt)
    if not m:
        #print("CASE 'not m'")
        return
    gr = m.groups()
    if gr:
        #print("CASE 'gr[0]'")
        return gr[0]
    #print("CASE 'm.group()'")
    return m.group()


def get_song_infos_from_deezer_website(search_type, id):
    url = "https://www.deezer.com/de/{}/{}".format(search_type, id)
    resp = deezer.session.get(url)
    assert resp.status_code == 200
    if "MD5_ORIGIN" not in resp.text:
        raise Exception("We are not logged in.")

    parser = ScriptExtractor()
    parser.feed(resp.text)
    parser.close()

    songs = []

    for script in parser.scripts:
        jsondata = find_re(script, r'{"DATA":.*')
        if jsondata:
            DZR_APP_STATE = json.loads(jsondata)
            if DZR_APP_STATE['DATA']['__TYPE__'] == 'playlist' or DZR_APP_STATE['DATA']['__TYPE__'] == 'album':
                # songs if you searched for album/playlist
                for song in DZR_APP_STATE['SONGS']['data']:
                    songs.append(song)
            elif DZR_APP_STATE['DATA']['__TYPE__'] == 'song':
                # just one song on that page
                songs.append(DZR_APP_STATE['DATA'])
    # always return a list
    return songs[0] if search_type == TYPE_TRACK else songs


def md5hex(data):
    """ return hex string of md5 of the given string """
    # type(data): bytes
    # returns: bytes
    h = MD5.new()
    h.update(data)
    return b2a_hex(h.digest())


def hexaescrypt(data, key):
    """ returns hex string of aes encrypted data """
    c = AES.new(key, AES.MODE_ECB)
    return b2a_hex(c.encrypt(data))


def genurlkey(songid, md5origin, mediaver=4, fmt=1):
    """ Calculate the deezer download url given the songid, origin and media+format """
    data_concat = b'\xa4'.join(_ for _ in [md5origin.encode(),
                                           str(fmt).encode(),
                                           str(songid).encode(),
                                           str(mediaver).encode()])
    data = b'\xa4'.join([md5hex(data_concat), data_concat]) + b'\xa4'
    if len(data) % 16 != 0:
        data += b'\0' * (16 - len(data) % 16)
    return hexaescrypt(data, "jo6aey6haid2Teih")


def calcbfkey(songid):
    """ Calculate the Blowfish decrypt key for a given songid """
    key = b"g4el58wc0zvf9na1"
    songid_md5 = md5hex(songid.encode())

    xor_op = lambda i: chr(songid_md5[i] ^ songid_md5[i + 16] ^ key[i])
    decrypt_key = "".join([xor_op(i) for i in range(16)])
    return decrypt_key


def blowfishDecrypt(data, key):
    iv = a2b_hex("0001020304050607")
    c = Blowfish.new(key, Blowfish.MODE_CBC, iv)
    return c.decrypt(data)


def decryptfile(fh, key, fo):
    """
    Decrypt data from file <fh>, and write to file <fo>.
    decrypt using blowfish with <key>.
    Only every third 2048 byte block is encrypted.
    """
    blockSize = 2048
    i = 0

    for data in fh.iter_content(blockSize):
        if not data:
            break

        isEncrypted = ((i % 3) == 0)
        isWholeBlock = len(data) == blockSize

        if isEncrypted and isWholeBlock:
            data = blowfishDecrypt(data, key)

        fo.write(data)
        i += 1



def writeid3v1_1(fo, song):
    
    # Bugfix changed song["SNG_TITLE... to song.get("SNG_TITLE... to avoid 'key-error' in case the key does not exist
    def song_get(song, key):
        try:
            return song.get(key).encode('utf-8')
            #return song.get(key)
        except Exception as e:
            return b""
        
    def album_get(key):
        global album_Data
        try:
            #return album_Data.get(key)
            return album_Data.get(key).encode('utf-8')
        except Exception as e:
            return b""    
    
#    print(type(b"TAG"))
#    print(type(song_get(song, "SNG_TITLE")))
#    print(type(song_get(song, "ART_NAME")))
#    print(type(song_get(song, "ALB_TITLE")))
#    print(type(album_get("PHYSICAL_RELEASE_DATE")))
#    print(type(album_get("LABEL_NAME")))
#    print(type(b"0"))
#    print(type(song_get(song, "TRACK_NUMBER")))
#    print(type(b"255"))
#            
#    print(b"TAG")
#    print(song_get(song, "SNG_TITLE"))
#    print(song_get(song, "ART_NAME"))
#    print(song_get(song, "ALB_TITLE"))
#    print(album_get("PHYSICAL_RELEASE_DATE"))
#    print(album_get("LABEL_NAME"))
#    print(b"0")
#    print(song_get(song, "TRACK_NUMBER"))
#    print(b"255")
#    set_trace()
   
    # what struct.pack expects
    # B => int
    # s => bytes
    data = struct.pack("3s" "30s" "30s" "30s" "4s" "28sB" "B"  "B", 
                       b"TAG",                                             # header
                       song_get(song, "SNG_TITLE"),                             # title
                       song_get(song, "ART_NAME"),                             # artist
                       song_get(song, "ALB_TITLE"),                             # album
                       album_get("PHYSICAL_RELEASE_DATE"),                # year
                       album_get("LABEL_NAME"), 0,                        # comment
                       int(song_get(song, "TRACK_NUMBER")),                # tracknum
                       255                                                # genre
                       )

    fo.write(data)


def downloadpicture(id):
    setting_domain_img = "https://e-cdns-images.dzcdn.net/images"
    url = setting_domain_img + "/cover/" + id + "/1200x1200.jpg"
    resp = deezer.session.get(url)
    # TODO: funktioniert das?
    return resp.content
#    try:
#
#        #fh = urllib2.urlopen(
#        fh = urllib.urlopen(
#            setting_domain_img + "/cover/" + id + "/1200x1200.jpg"
#        )
#        return fh.read()
#
#    except Exception as e:
#        print("no pic", e)


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
#>      big-endian
#s      char[]  bytes
#H      unsigned short  integer 2
#B      unsigned char   integer 1
#L      unsigned long   integer 4


    hdr = struct.pack(">" 
                      "3s" "H" "B" "L", 
                      "ID3".encode("ascii"),
                      0x300,   # version
                      0x00,    # flags
                      make28bit( len( id3data) ) )

    fo.write(hdr)
    fo.write(id3data)


def deezer_search(search, type):
    search = urllib.parse.quote_plus(search)
    resp = deezer.session.get("https://api.deezer.com/search/{}?q={}".format(type, search))
    return_nice = []
    for item in resp.json()['data'][:10]:
        i = {}
        i['id'] = str(item['id'])
        if type == TYPE_ALBUM:
            i['album'] = item['title']
            i['artist'] = item['artist']['name']
            i['title'] = ''
        if type == TYPE_TRACK:
            i['title'] = item['title']
            i['album'] = item['album']['title']
            i['artist'] = item['artist']['name']
        return_nice.append(i)
    return return_nice


#def sorted_nicely(l):
#    """ Sorts the given iterable in the way that is expected.
#
#    Required arguments:
#    l -- The iterable to be sorted.
#
#    """
#    print("TODO: sorted_nicely kann das nicht weg?")
#    convert = lambda text: int(text) if text.isdigit() else text
#    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
#    l = [x for x in l if x]
#    return sorted(l, key=alphanum_key)


def make_song_paths_relative_to_mpd_root(songs):
    global mpd_music_dir_root
    if not mpd_music_dir_root.endswith("/"):
        mpd_music_dir_root += "/"
    songs_paths_relative_to_mpd_root = []
    for song in songs:
        songs_paths_relative_to_mpd_root.append(song[len(mpd_music_dir_root):])
    return songs_paths_relative_to_mpd_root


def update_mpd_db(songs, add_to_playlist):
    # songs: list of music files or just a string (file path)
    print("Updating mpd database")
    timeout_counter = 0
    mpd_client = mpd.MPDClient(use_unicode=True)
    try:
        mpd_client.connect(mpd_host, mpd_port)
    except ConnectionRefusedError as e:
        print("ERROR connecting to MPD ({}:{}): {}".format(mpd_host, mpd_port, e))
        return
    mpd_client.update()
    if add_to_playlist:
        songs = [songs] if type(songs) != list else songs
        songs = make_song_paths_relative_to_mpd_root(songs)
        while len(mpd_client.search("file", songs[0])) == 0:
            # c.update() does not block so wait for it
            if timeout_counter == 10:
                print("Tried it {} times. Give up now.".format(timeout_counter))
                return
            print("'{}' not found in the music db. Let's wait for it".format(songs[0]))
            timeout_counter += 1
            time.sleep(2)
        for song in songs:
            mpd_client.add(song)
            print("Added to mpd playlist: '{}'".format(song))



#def my_download_from_json_file():
#    songs = json.load(open("/tmp/songs.json"))
#    for song in songs['results']['SONGS']['data']:
#        print("Downloading {}".format(song['SNG_TITLE']))
#        download(song)


def parse_deezer_playlist(playlist_id):
    req = deezer.session.post("https://www.deezer.com/ajax/gw-light.php?method=deezer.getUserData&input=3&api_version=1.0&api_token=")
    csrf_token = req.json()['results']['checkForm']

    url = "https://www.deezer.com/ajax/gw-light.php?method=deezer.pagePlaylist&input=3&api_version=1.0&api_token={}".format(csrf_token)
    data = {'playlist_id': int(playlist_id),
            'start': 0,
            'tab': 0,
            'header': True,
            'lang': 'de',
            'nb': 500}
    req = deezer.session.post(url, json=data)
    j = req.json()

    if len(j['error']) > 0:
        print("ERROR: deezer api said {}".format(j['error']))
        return
    j = j['results']

    playlist_name = j['DATA']['TITLE']
    number_songs = j['DATA']['NB_SONG']
    print("Playlist {} with {} songs".format(playlist_name, number_songs))

    print("Got {} songs from API".format(j['SONGS']['count']))
    return playlist_name, j['SONGS']['data']


class FileAlreadyExists(Exception):
    pass


def get_absolute_filename(type, song, playlist_name=None):
    file_exist = False

    # TODO: filter and sanitize filename /
    # TODO: assert  playlist_name gesetzt wenn TYPE == PLAYLIST + / raus
    song_filename = "{} - {}.mp3".format(song['ART_NAME'], song['SNG_TITLE'])

    if type == TYPE_TRACK:
        absolute_filename = os.path.join(deezer_download_dir_songs, song_filename)
            #raise FileAlreadyExists("Skipping song '{}'. Already exists.".format(absolute_filename))
            # TODO: das printete nur lädt aber trotzdem neu
    elif type == TYPE_ALBUM:
        # TODO: sanizize album_name
        album_name = "{} - {}".format(song['ART_NAME'], song['ALB_TITLE'])
        #song_filename = "{} - {}.mp3".format(song['ART_NAME'], song['SNG_TITLE'])
        album_dir = os.path.join(deezer_download_dir_albums, album_name)
        if not os.path.exists(album_dir):
            os.mkdir(album_dir)
        absolute_filename = os.path.join(album_dir, song_filename)
    elif type == TYPE_PLAYLIST:
        assert playlist_name is not None
        playlist_dir = os.path.join(download_dir_playlists, playlist_name)
        if not os.path.exists(playlist_dir):
            os.mkdir(playlist_dir)
        absolute_filename = os.path.join(playlist_dir, song_filename)

    if os.path.exists(absolute_filename):
        file_exist = True

    if file_exist:
        print("Skipping song '{}'. Already exists.".format(absolute_filename))
    else:
        print("Downloading '{}'".format(song_filename))
    return (file_exist, absolute_filename)


def download_song(song, output_file):

    song_quality = 3 if song.get("FILESIZE_MP3_320") else \
                   5 if song.get("FILESIZE_MP3_256") else \
                   1
    song_quality = 1

    #return 8 if song.get("FILESIZE_FLAC") else \
    # TODO: geht da mehr?
    urlkey = genurlkey(song["SNG_ID"], song["MD5_ORIGIN"], song["MEDIA_VERSION"], song_quality)
    key = calcbfkey(song["SNG_ID"])
    try:
        url = "https://e-cdns-proxy-%s.dzcdn.net/mobile/1/%s" % (song["MD5_ORIGIN"][0], urlkey.decode())
        #print(url)
        fh = deezer.session.get(url)
        if fh.status_code != 200:
            #set_trace()

            return
        assert fh.status_code == 200

        with open(output_file, "w+b") as fo:
            # add songcover and DL first 30 sec's that are unencrypted
            writeid3v2(fo, song)
            decryptfile(fh, key, fo)
            writeid3v1_1(fo, song)

#        toWS = MP3(output_file, ID3=ID3)
#        try:
#            toWS.add_tags()
#        except:
#            pass
#
#        toWS.tags.add(
#            APIC(
#                encoding=3,         # 3 is for utf-8
#                mime='image/jpeg',  # image/jpeg or image/png
#                type=3,             # 3 is for the cover image
#                desc=u'Cover',
#                data=downloadpicture(song["ALB_PICTURE"])
#            )
#        )
#        toWS.save(v2_version=3)

    except Exception as e:
        raise
    else:
        print("Dowload finished: {}".format(output_file))
    #return os.path.join(download_dir[len(music_dir) + 1 :] ,f) # (deezer download dir - download dir) + file name of the downloaded file


def create_zip_file(songs_absolute_location):
    # take first song in list and take the parent dir (name of album/playlist")
    name_zipfile = songs_absolute_location[0].split("/")[-2] + ".zip"
    location_zip_file = os.path.join(download_dir_zips, name_zipfile)
    print("Creating zip file '{}'".format(location_zip_file))
    parent_dir = songs_absolute_location[0].split("/")[-2]
    with ZipFile(location_zip_file, 'w', compression=ZIP_DEFLATED) as zip:
        for song_location in songs_absolute_location:
            print("Adding song {}".format(song_location))
            zip.write(song_location, arcname="{}/{}".format(parent_dir, basename(song_location)))
    print("Done with the zip")


def create_m3u8_file(songs_absolute_location):
    playlist_directory, __ = os.path.split(songs_absolute_location[0])
    m3u8_filename = playlist_directory.split("/")[-1] + ".m3u8"
    print("Creating m3u8 file: '{}'".format(m3u8_filename))
    m3u8_file_abs = os.path.join(playlist_directory, m3u8_filename)
    with open(m3u8_file_abs, "w") as f:
        for song in songs_absolute_location:
            f.write(basename(song) + "\n")


def download_deezer_song_and_queue(track_id, add_to_playlist):
    song = get_song_infos_from_deezer_website(TYPE_TRACK, track_id)
    file_exist, absolute_filename = get_absolute_filename(TYPE_TRACK, song)
    if not file_exist:
        download_song(song, absolute_filename)
    if use_mpd:
        update_mpd_db(absolute_filename, add_to_playlist)


def download_deezer_album_and_queue_and_zip(album_id, add_to_playlist, create_zip):
    songs = get_song_infos_from_deezer_website(TYPE_ALBUM, album_id)
    songs_absolute_location = []
    for song in songs:
        assert type(song) == dict
        file_exist, absolute_filename = get_absolute_filename(TYPE_ALBUM, song)
        if not file_exist:
            download_song(song, absolute_filename)
        songs_absolute_location.append(absolute_filename)
    if use_mpd:
        update_mpd_db(songs_absolute_location, add_to_playlist)
    if create_zip:
        create_zip_file(songs_absolute_location)

def download_deezer_playlist_and_queue_and_zip(playlist_id, add_to_playlist, create_zip):
    playlist_name, songs = parse_deezer_playlist(playlist_id)
    songs_absolute_location = []
    for song in songs:
        # TODO: sanizie playlist_name
        file_exist, absolute_filename = get_absolute_filename(TYPE_PLAYLIST, song, playlist_name)
        if not file_exist:
            download_song(song, absolute_filename)
        songs_absolute_location.append(absolute_filename)
    if use_mpd:
        update_mpd_db(songs_absolute_location, add_to_playlist)
    if create_zip:
        create_zip_file(songs_absolute_location)

def download_spotify_playlist_and_queue_and_zip(playlist_name, playlist_id, add_to_playlist, create_zip):
    songs = get_songs_from_spotify_website(playlist_id)
    if not songs:
        return
    songs_absolute_location = []
    for song_of_playlist in songs:
        # song_of_playlist: string (artist - song)
        try:
            track_id = deezer_search(song_of_playlist, TYPE_TRACK)[0]['id'] #[0] can throw IndexError
            song = get_song_infos_from_deezer_website(TYPE_TRACK, track_id)
            file_exist, absolute_filename = get_absolute_filename(TYPE_PLAYLIST, song, playlist_name)
            if not file_exist:
                download_song(song, absolute_filename)
            songs_absolute_location.append(absolute_filename)
        except IndexError:
            print("Found no song on Deezer for '{}' from Spotify playlist".format(song_of_playlist))
    create_m3u8_file(songs_absolute_location)
    if use_mpd:
        update_mpd_db(songs_absolute_location, add_to_playlist)
    if create_zip:
        create_zip_file(songs_absolute_location)


def download_youtubedl_and_queue(video_url, add_to_playlist):
    try:
        filename_absolute = youtubedl_download(video_url, youtubedl_download_dir)
    except (YoutubeDLFailedException, DownloadedFileNotFoundException) as msg:
        print(msg)
        return
    if use_mpd:
        update_mpd_db(filename_absolute, add_to_playlist)


if __name__ == '__main__':
    pass
    #my_download_song("2271563", True, True)
    #my_download_album("93769922", create_zip=True)
    #export_download_song("2271563", update_mpd=False, add_to_playlist=False)

    #full = "/tmp/music/deezer/Twenty One Pilots - Vessel"
    #list_files = [os.path.join(full, x) for x in os.listdir(full)]
    #print(list_files)
    #create_zip_file(list_files)
    #video_url = "https://www.invidio.us/watch?v=ZbZSe6N_BXs"
    #export_download_youtubedl(video_url, False)

    #full = "/tmp/music/deezer/spotify-playlists/this is a playlist/"
    #list_files = [os.path.join(full, x) for x in os.listdir(full)]
    #create_m3u8(list_files)
    playlist_id = "878989033"
    playlist_id = "1180748301"
    download_deezer_playlist_and_queue_and_zip(playlist_id, False, True)
