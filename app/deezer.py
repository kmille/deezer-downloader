import sys
import re
import json
import threading

from configuration import config

from Crypto.Hash import MD5
from Crypto.Cipher import AES, Blowfish
import struct
import urllib.parse
import html.parser
import requests
from binascii import a2b_hex, b2a_hex


# BEGIN TYPES
TYPE_TRACK = "track"
TYPE_ALBUM = "album"
TYPE_PLAYLIST = "playlist"
TYPE_ALBUM_TRACK = "album_track" # used for listing songs of an album
# END TYPES

session = None


def init_deezer_session():
    global session
    header = {
        'Pragma': 'no-cache',
        'Origin': 'https://www.deezer.com',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Accept': '*/*',
        'Cache-Control': 'no-cache',
        'X-Requested-With': 'XMLHttpRequest',
        'Connection': 'keep-alive',
        'Referer': 'https://www.deezer.com/login',
        'DNT': '1',
    }
    session = requests.session()
    session.headers.update(header)
    session.cookies.update({'sid': config['deezer']['sid'], 'comeback': '1'})


init_deezer_session()


class Deezer404Exception(Exception):
    pass


class Deezer403Exception(Exception):
    pass


class DeezerApiException(Exception):
    pass


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
        except:
            return b""

    def album_get(key):
        global album_Data
        try:
            return album_Data.get(key).encode('utf-8')
        except:
            return b""

    # what struct.pack expects
    # B => int
    # s => bytes
    data = struct.pack("3s" "30s" "30s" "30s" "4s" "28sB" "B"  "B",
                       b"TAG",                                            # header
                       song_get(song, "SNG_TITLE"),                       # title
                       song_get(song, "ART_NAME"),                        # artist
                       song_get(song, "ALB_TITLE"),                       # album
                       album_get("PHYSICAL_RELEASE_DATE"),                # year
                       album_get("LABEL_NAME"), 0,                        # comment
                       int(song_get(song, "TRACK_NUMBER")),               # tracknum
                       255                                                # genre
                       )

    fo.write(data)


def downloadpicture(pic_idid):
    resp = session.get(get_picture_link(pic_idid))
    return resp.content


def get_picture_link(pic_idid):
    setting_domain_img = "https://e-cdns-images.dzcdn.net/images"
    url = setting_domain_img + "/cover/" + pic_idid + "/1200x1200.jpg"
    return url


def writeid3v2(fo, song):

    def make28bit(x):
        return ((x << 3) & 0x7F000000) | ((x << 2) & 0x7F0000) | (
               (x << 1) & 0x7F00) | (x & 0x7F)

    def maketag(tag, content):
        return struct.pack(">4sLH", tag.encode("ascii"), len(content), 0) + content

    def album_get(key):
        global album_Data
        try:
            return album_Data.get(key)
        except:
            #raise
            return ""

    def song_get(song, key):
        try:
            return song[key]
        except:
            #raise
            return ""

    def makeutf8(txt):
        #return b"\x03" + txt.encode('utf-8')
        return "\x03{}".format(txt).encode()

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
        imgframe = (b"\x00",                 # text encoding
                    b"image/jpeg", b"\0",    # mime type
                    b"\x03",                 # picture type: 'Cover (front)'
                    b""[:64], b"\0",         # description
                    data
                    )

        return b'' .join(imgframe)

    # get Data as DDMM
    try:
        phyDate_YYYYMMDD = album_get("PHYSICAL_RELEASE_DATE") .split('-') #'2008-11-21'
        phyDate_DDMM = phyDate_YYYYMMDD[2] + phyDate_YYYYMMDD[1]
    except:
        phyDate_DDMM = ''

    # get size of first item in the list that is not 0
    try:
        FileSize = [
            song_get(song, i)
            for i in (
                'FILESIZE_AAC_64',
                'FILESIZE_MP3_320',
                'FILESIZE_MP3_256',
                'FILESIZE_MP3_64',
                'FILESIZE',
                ) if song_get(song, i)
            ][0]
    except:
        FileSize = 0

    try:
        track = "%02s" % song["TRACK_NUMBER"]
        track += "/%02s" % album_get("TRACKS")
    except:
        pass

    # http://id3.org/id3v2.3.0#Attached_picture
    id3 = [
        maketag("TRCK", makeutf8(track)),     # The 'Track number/Position in set' frame is a numeric string containing the order number of the audio-file on its original recording. This may be extended with a "/" character and a numeric string containing the total numer of tracks/elements on the original recording. E.g. "4/9".
        maketag("TLEN", makeutf8(str(int(song["DURATION"]) * 1000))),     # The 'Length' frame contains the length of the audiofile in milliseconds, represented as a numeric string.
        maketag("TORY", makeutf8(str(album_get("PHYSICAL_RELEASE_DATE")[:4]))),     # The 'Original release year' frame is intended for the year when the original recording was released. if for example the music in the file should be a cover of a previously released song
        maketag("TYER", makeutf8(str(album_get("DIGITAL_RELEASE_DATE")[:4]))),     # The 'Year' frame is a numeric string with a year of the recording. This frames is always four characters long (until the year 10000).
        maketag("TDAT", makeutf8(str(phyDate_DDMM))),     # The 'Date' frame is a numeric string in the DDMM format containing the date for the recording. This field is always four characters long.
        maketag("TPUB", makeutf8(album_get("LABEL_NAME"))),     # The 'Publisher' frame simply contains the name of the label or publisher.
        maketag("TSIZ", makeutf8(str(FileSize))),     # The 'Size' frame contains the size of the audiofile in bytes, excluding the ID3v2 tag, represented as a numeric string.
        maketag("TFLT", makeutf8("MPG/3")),

        ]  # decimal, no term NUL
    id3.extend([
        maketag(ID_id3_frame, makeutf8(song_get(song, ID_song))) for (ID_id3_frame, ID_song) in \
        (
            ("TALB", "ALB_TITLE"),   # The 'Album/Movie/Show title' frame is intended for the title of the recording(/source of sound) which the audio in the file is taken from.
            ("TPE1", "ART_NAME"),   # The 'Lead artist(s)/Lead performer(s)/Soloist(s)/Performing group' is used for the main artist(s). They are seperated with the "/" character.
            ("TPE2", "ART_NAME"),   # The 'Band/Orchestra/Accompaniment' frame is used for additional information about the performers in the recording.
            ("TPOS", "DISK_NUMBER"),   # The 'Part of a set' frame is a numeric string that describes which part of a set the audio came from. This frame is used if the source described in the "TALB" frame is divided into several mediums, e.g. a double CD. The value may be extended with a "/" character and a numeric string containing the total number of parts in the set. E.g. "1/2".
            ("TIT2", "SNG_TITLE"),   # The 'Title/Songname/Content description' frame is the actual name of the piece (e.g. "Adagio", "Hurricane Donna").
            ("TSRC", "ISRC"),   # The 'ISRC' frame should contain the International Standard Recording Code (ISRC) (12 characters).
        )
    ])

    try:
        id3.append(maketag("APIC", makepic(downloadpicture(song["ALB_PICTURE"]))))
    except Exception as e:
        print("ERROR: no album cover?", e)

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
                      make28bit(len(id3data)))

    fo.write(hdr)
    fo.write(id3data)


def download_song(song, output_file):
    # downloads and decrypts the song from Deezer. Adds ID3 and art cover
    # song: dict with information of the song (grabbed from Deezer.com)
    # output_file: absolute file name of the output file
    assert type(song) == dict, "song must be a dict"
    assert type(output_file) == str, "output_file must be a str"

    #song_quality = 8 if song.get("FILESIZE_FLAC") else \ # needs premium subscription, untested
    song_quality = 3 if song.get("FILESIZE_MP3_320") else \
                   5 if song.get("FILESIZE_MP3_256") else \
                   1

    urlkey = genurlkey(song["SNG_ID"], song["MD5_ORIGIN"], song["MEDIA_VERSION"], song_quality)
    key = calcbfkey(song["SNG_ID"])
    try:
        url = "https://e-cdns-proxy-%s.dzcdn.net/mobile/1/%s" % (song["MD5_ORIGIN"][0], urlkey.decode())
        fh = session.get(url)
        if fh.status_code != 200:
            # I don't why this happens. to reproduce:
            # go to https://www.deezer.com/de/playlist/1180748301
            # search for Moby
            # open in a new tab the song Moby - Honey
            # this will give you a 404!?
            # but you can play the song in the browser
            print("ERROR: Can not download this song. Got a {}".format(fh.status_code))
            return

        with open(output_file, "w+b") as fo:
            # add songcover and DL first 30 sec's that are unencrypted
            writeid3v2(fo, song)
            decryptfile(fh, key, fo)
            writeid3v1_1(fo, song)

    except Exception as e:
        raise
    else:
        print("Dowload finished: {}".format(output_file))


def get_song_infos_from_deezer_website(search_type, id):
    # search_type: either one of the constants: TYPE_TRACK|TYPE_ALBUM|TYPE_PLAYLIST
    # id: deezer_id of the song/album/playlist (like https://www.deezer.com/de/track/823267272)
    # return: if TYPE_TRACK => song (dict grabbed from the website with information about a song)
    # return: if TYPE_ALBUM|TYPE_PLAYLIST => list of songs
    # raises
    # Deezer404Exception if
    # 1. open playlist https://www.deezer.com/de/playlist/1180748301 and click on song Honey from Moby in a new tab:
    # 2. Deezer gives you a 404: https://www.deezer.com/de/track/68925038
    # Deezer403Exception if we are not logged in

    url = "https://www.deezer.com/de/{}/{}".format(search_type, id)
    resp = session.get(url)
    if resp.status_code == 404:
        raise Deezer404Exception("ERROR: Got a 404 for {} from Deezer".format(url))
    if "MD5_ORIGIN" not in resp.text:
        raise Deezer403Exception("ERROR: we are not logged in on deezer.com")

    parser = ScriptExtractor()
    parser.feed(resp.text)
    parser.close()

    songs = []
    for script in parser.scripts:
        regex = re.search(r'{"DATA":.*', script)
        if regex:
            DZR_APP_STATE = json.loads(regex.group())
            global album_Data
            album_Data = DZR_APP_STATE.get("DATA")
            if DZR_APP_STATE['DATA']['__TYPE__'] == 'playlist' or DZR_APP_STATE['DATA']['__TYPE__'] == 'album':
                # songs if you searched for album/playlist
                for song in DZR_APP_STATE['SONGS']['data']:
                    songs.append(song)
            elif DZR_APP_STATE['DATA']['__TYPE__'] == 'song':
                # just one song on that page
                songs.append(DZR_APP_STATE['DATA'])
    return songs[0] if search_type == TYPE_TRACK else songs


def deezer_search(search, search_type):
    # search: string (What are you looking for?)
    # search_type: either one of the constants: TYPE_TRACK|TYPE_ALBUM|TYPE_ALBUM_TRACK (TYPE_PLAYLIST is not supported)
    # return: list of dicts (keys depend on search_type)

    if search_type not in [TYPE_TRACK, TYPE_ALBUM, TYPE_ALBUM_TRACK]:
        print("ERROR: search_type is wrong: {}".format(search_type))
        return []
    search = urllib.parse.quote_plus(search)
    if search_type == TYPE_ALBUM_TRACK:
        resp = get_song_infos_from_deezer_website(TYPE_ALBUM, search)
    else:
        resp = session.get("https://api.deezer.com/search/{}?q={}".format(search_type, search)).json()['data']
    return_nice = []
    for item in resp:
        i = {}
        if search_type == TYPE_ALBUM:
            i['id'] = str(item['id'])
            i['id_type'] = TYPE_ALBUM
            i['album'] = item['title']
            i['album_id'] = item['id']
            i['img_url'] = item['cover_small']
            i['artist'] = item['artist']['name']
            i['title'] = ''
            i['preview_url'] = ''

        if search_type == TYPE_TRACK:
            i['id'] = str(item['id'])
            i['id_type'] = TYPE_TRACK
            i['title'] = item['title']
            i['img_url'] = item['album']['cover_small']
            i['album'] = item['album']['title']
            i['album_id'] = item['album']['id']
            i['artist'] = item['artist']['name']
            i['preview_url'] = item['preview']

        if search_type == TYPE_ALBUM_TRACK:
            i['id'] = str(item['SNG_ID'])
            i['id_type'] = TYPE_TRACK
            i['title'] = item['SNG_TITLE']
            i['img_url'] = '' # item['album']['cover_small']
            i['album'] = item['ALB_TITLE']
            i['album_id'] = item['ALB_ID']
            i['artist'] = item['ART_NAME']
            i['preview_url'] = next(media['HREF'] for media in item['MEDIA'] if media['TYPE'] == 'preview')

        return_nice.append(i)
    return return_nice


def parse_deezer_playlist(playlist_id):
    # playlist_id: id of the playlist or the url of it
    # e.g. https://www.deezer.com/de/playlist/6046721604 or 6046721604
    # return (playlist_name, list of songs) (song is a dict with information about the song)
    # raises DeezerApiException if something with the Deezer API is broken

    try:
        playlist_id = re.search(r'\d+', playlist_id).group(0)
    except AttributeError:
        raise DeezerApiException("ERROR: Regex (\\d+) for playlist_id failed. You gave me '{}'".format(playlist_id))

    url_get_csrf_token = "https://www.deezer.com/ajax/gw-light.php?method=deezer.getUserData&input=3&api_version=1.0&api_token="
    req = session.post(url_get_csrf_token)
    csrf_token = req.json()['results']['checkForm']

    url_get_playlist_songs = "https://www.deezer.com/ajax/gw-light.php?method=deezer.pagePlaylist&input=3&api_version=1.0&api_token={}".format(csrf_token)
    data = {'playlist_id': int(playlist_id),
            'start': 0,
            'tab': 0,
            'header': True,
            'lang': 'de',
            'nb': 500}
    req = session.post(url_get_playlist_songs, json=data)
    json = req.json()

    if len(json['error']) > 0:
        raise DeezerApiException("ERROR: deezer api said {}".format(json['error']))
    json_data = json['results']

    playlist_name = json_data['DATA']['TITLE']
    number_songs = json_data['DATA']['NB_SONG']
    print("Playlist '{}' has {} songs".format(playlist_name, number_songs))

    print("Got {} songs from API".format(json_data['SONGS']['count']))
    return playlist_name, json_data['SONGS']['data']


_keepalive_timer = None
_deezer_is_working = False


def start_deezer_keepalive():
    global _keepalive_timer

    test_deezer_login()

    _keepalive_timer = threading.Timer(60.0 * config.getint('deezer', 'keepalive'), start_deezer_keepalive)
    _keepalive_timer.start()


def stop_deezer_keepalive():
    if _keepalive_timer is not None:
        _keepalive_timer.cancel()


def is_deezer_session_valid():
    return _deezer_is_working


def test_deezer_login():
    global _deezer_is_working
    # sid cookie has no expire date. Session will be extended on the server side
    # so we will just send a request regularly to not get logged out
    print("Let's check if the deezer login is still working")
    try:
        song = get_song_infos_from_deezer_website(TYPE_TRACK, "917265")
    except (Deezer403Exception, Deezer404Exception) as msg:
        print(msg)
        print("Login is not working anymore.")
        _deezer_is_working = False
        return False

    if song:
        print("Login is still working.")
        _deezer_is_working = True
        return True
    else:
        print("Login is not working anymore.")
        _deezer_is_working = False
        return False


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "check-login":
        test_deezer_login()
