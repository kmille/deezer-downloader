import sys
import re
import json
from typing import Optional, Sequence

from deezer_downloader.configuration import config

from Crypto.Hash import MD5
from Crypto.Cipher import Blowfish
import urllib.parse
import html.parser
import requests
from binascii import a2b_hex, b2a_hex
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import PictureType, TIT2, TALB, TPE1, TRCK, TDRC, TPOS, APIC, TPE2
from mutagen import MutagenError


# BEGIN TYPES
TYPE_TRACK = "track"
TYPE_ALBUM = "album"
TYPE_PLAYLIST = "playlist"
TYPE_ARTIST = "artist"
TYPE_ALBUM_TRACK = "album_track" # used for listing songs of an album
TYPE_ARTIST_ALBUM = "artist_album" # used for listing albums of an artist
TYPE_ARTIST_TOP = "artist_top" # used for listing top tracks of an artist
# END TYPES

session = None
license_token = {}
sound_format = ""
USER_AGENT = "Mozilla/5.0 (X11; Linux i686; rv:135.0) Gecko/20100101 Firefox/135.0"


def get_user_data() -> tuple[str, str]:
    try:
        user_data = session.get('https://www.deezer.com/ajax/gw-light.php?method=deezer.getUserData&input=3&api_version=1.0&api_token=')
        user_data_json = user_data.json()['results']
        options = user_data_json['USER']['OPTIONS']
        license_token = options['license_token']
        web_sound_quality = options['web_sound_quality']
        return license_token, web_sound_quality
    except (requests.exceptions.RequestException, KeyError) as e:
        print(f"ERROR: Could not get license token: {e}")


# quality_config comes from config file
# web_sound_quality is a dict coming from Deezer API and depends on ARL cookie (premium subscription)
def set_song_quality(quality_config: str, web_sound_quality: dict):
    global sound_format
    flac_supported = web_sound_quality['lossless'] is True
    if flac_supported:
        if quality_config == "flac":
            sound_format = "FLAC"
        else:
            sound_format = "MP3_320"
    else:
        if quality_config == "flac":
            print("WARNING: flac quality is configured in config file but not supported (no premium subscription?). Falling back to mp3")
        sound_format = "MP3_128"


def get_file_extension() -> str:
    return "flac" if sound_format == "FLAC" else "mp3"


# quality is mp3 or flac
def init_deezer_session(proxy_server: str, quality: str) -> None:
    global session, license_token, web_sound_quality
    header = {
        'Pragma': 'no-cache',
        'Origin': 'https://www.deezer.com',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9',
        'User-Agent': USER_AGENT,
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
    session.cookies.update({'arl': config['deezer']['cookie_arl'], 'comeback': '1'})
    if len(proxy_server.strip()) > 0:
        print(f"Using proxy {proxy_server}")
        session.proxies.update({"https": proxy_server})
    license_token, web_sound_quality = get_user_data()
    set_song_quality(quality, web_sound_quality)


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


def calcbfkey(songid):
    """ Calculate the Blowfish decrypt key for a given songid """
    key = b"g4el58wc0zvf9na1"
    songid_md5 = md5hex(songid.encode())

    xor_op = lambda i: chr(songid_md5[i] ^ songid_md5[i + 16] ^ key[i])
    decrypt_key = "".join([xor_op(i) for i in range(16)])
    return decrypt_key


def blowfishDecrypt(data, key):
    iv = a2b_hex("0001020304050607")
    c = Blowfish.new(key.encode(), Blowfish.MODE_CBC, iv)
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


def downloadpicture(pic_idid):
    setting_domain_img = "https://e-cdns-images.dzcdn.net/images"
    url = setting_domain_img + "/cover/" + pic_idid + "/1200x1200.jpg"
    resp = session.get(url)
    resp.raise_for_status()
    return resp.content


def get_song_url(track_token: str, quality: int = 3) -> str:
    try:
        response = requests.post(
            "https://media.deezer.com/v1/get_url",
            json={
                'license_token': license_token,
                'media': [{
                    'type': "FULL",
                    "formats": [
                        {"cipher": "BF_CBC_STRIPE", "format": sound_format}]
                }],
                'track_tokens': [track_token,]
            },
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Could not retrieve song URL: {e}")

    if not data.get('data') or 'errors' in data['data'][0]:
        raise RuntimeError(f"Could not get download url from API: {data['data'][0]['errors'][0]['message']}")

    if len(data["data"][0]["media"]) == 0:
        raise RuntimeError(f"Could not get download url from API. There was no API error, but also no song information. API response: {data}")

    url = data['data'][0]['media'][0]['sources'][0]['url']
    return url


def download_song(song: dict, output_file: str) -> None:
    # downloads and decrypts the song from Deezer. Adds ID3 and art cover
    # song: dict with information of the song (grabbed from Deezer.com)
    # output_file: absolute file name of the output file
    assert type(song) is dict, "song must be a dict"
    assert type(output_file) is str, "output_file must be a str"

    try:
        url = get_song_url(song["TRACK_TOKEN"])
    except Exception as e:
        print(f"Could not download song (https://www.deezer.com/us/track/{song['SNG_ID']}). Maybe it's not available anymore or at least not in your country. {e}")
        if "FALLBACK" in song:
            song = song["FALLBACK"]
            print(f"Trying fallback song https://www.deezer.com/us/track/{song['SNG_ID']}")
            try:
                url = get_song_url(song["TRACK_TOKEN"])
            except Exception:
                pass
            else:
                print("Fallback song seems to work")
        else:
            raise

    key = calcbfkey(song["SNG_ID"])
    is_flac = get_file_extension() == "flac"

    try:
        with session.get(url, stream=True) as response:
            response.raise_for_status()
            with open(output_file, "w+b") as fo:
                decryptfile(response, key, fo)
        write_song_metadata(output_file, song, is_flac)
    except MutagenError as e:
        print(f"Warning: Could not write metadata to file: {e}")
    except Exception as e:
        raise DeezerApiException(f"Could not write song to disk: {e}") from e
    print("Download finished: {}".format(output_file))


def write_song_metadata(output_file: str, song: dict, is_flac: bool) -> None:

    def set_metadata(audio, key, value):
        if not value:
            return
        elif isinstance(audio, MP3):
            if key == 'artist':
                audio['TPE1'] = TPE1(encoding=3, text=value)
            elif key == 'albumartist':
                audio['TPE2'] = TPE2(encoding=3, text=value)
            elif key == 'title':
                audio['TIT2'] = TIT2(encoding=3, text=value)
            elif key == 'album':
                audio['TALB'] = TALB(encoding=3, text=value)
            elif key == 'discnumber':
                audio['TPOS'] = TPOS(encoding=3, text=value)
            elif key == 'tracknumber':
                audio['TRCK'] = TRCK(encoding=3, text=value)
            elif key == 'date':
                audio['TDRC'] = TDRC(encoding=3, text=value)
            elif key == 'picture':
                audio['APIC'] = APIC(encoding=3, mime='image/jpeg', type=PictureType.COVER_FRONT, desc='Cover', data=value)
        else:
            if key == 'picture':
                pic = Picture()
                pic.mime = u'image/jpeg'
                pic.type = PictureType.COVER_FRONT
                pic.desc = 'Cover'
                pic.data = value
                audio.add_picture(pic)
            else:
                audio[key] = value

    if is_flac:
        audio = FLAC(output_file)
    else:
        audio = MP3(output_file)

    set_metadata(audio, "artist", song.get("ART_NAME", None))
    set_metadata(audio, "title", song.get("SNG_TITLE", None))
    set_metadata(audio, "album", song.get("ALB_TITLE", None))
    set_metadata(audio, 'tracknumber', song.get("TRACK_NUMBER", None))
    set_metadata(audio, "discnumber", song.get("DISK_NUMBER", None))

    if "album_Data" in globals() and "PHYSICAL_RELEASE_DATE" in album_Data:
        set_metadata(audio, "date", album_Data.get("PHYSICAL_RELEASE_DATE")[:4])

    set_metadata(audio, "picture", downloadpicture(song["ALB_PICTURE"]))
    set_metadata(audio, "albumartist", song.get('ALB_ART_NAME', song.get('ART_NAME', None)))
    audio.save()


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

    url = "https://www.deezer.com/us/{}/{}".format(search_type, id)
    resp = session.get(url)
    if resp.status_code == 404:
        raise Deezer404Exception("ERROR: Got a 404 for {} from Deezer".format(url))
    if "MD5_ORIGIN" not in resp.text:
        raise Deezer403Exception("ERROR: we are not logged in on deezer.com. Please update the cookie")

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

    if search_type not in [TYPE_TRACK, TYPE_ALBUM, TYPE_ARTIST, TYPE_ALBUM_TRACK, TYPE_ARTIST_ALBUM, TYPE_ARTIST_TOP]:
        print("ERROR: search_type is wrong: {}".format(search_type))
        return []
    search = urllib.parse.quote_plus(search)
    if search_type == TYPE_ALBUM_TRACK:
        url = f"https://api.deezer.com//album/{search}"
    elif search_type == TYPE_ARTIST_TOP:
        url = f"https://api.deezer.com/artist/{search}/top?limit=20"
    elif search_type == TYPE_ARTIST_ALBUM:
        url = f"https://api.deezer.com/artist/{search}/albums"
    else:
        url = f"https://api.deezer.com/search/{search_type}?q={search}"

    try:
        resp = session.get(url)
        resp.raise_for_status()
        data = resp.json()
        if search_type == TYPE_ALBUM_TRACK:
            data = data["tracks"]['data']
        else:
            data = data['data']
    except (requests.exceptions.RequestException, KeyError) as e:
        print(f"ERROR: Could not search for music: {e}")
        return []

    return_nice = []
    for item in data:
        i = {}
        i['id'] = str(item['id'])
        if search_type in (TYPE_ALBUM, TYPE_ARTIST_ALBUM):
            i['id_type'] = TYPE_ALBUM
            i['album'] = item['title']
            i['album_id'] = item['id']
            i['img_url'] = item['cover_small']
            i['title'] = ''
            i['preview_url'] = ''
            i['artist'] = ''
            if search_type == TYPE_ALBUM:
                # strange API design? artist is not there when asking for ARTIST_ALBUMs
                i['artist'] = item['artist']['name']
        elif search_type in (TYPE_TRACK, TYPE_ARTIST_TOP, TYPE_ALBUM_TRACK):
            i['id_type'] = TYPE_TRACK
            i['title'] = item['title']
            i['img_url'] = item['album']['cover_small']
            i['album'] = item['album']['title']
            i['album_id'] = item['album']['id']
            i['artist'] = item['artist']['name']
            i['preview_url'] = item['preview']
        elif search_type == TYPE_ARTIST:
            i['id_type'] = TYPE_ARTIST
            i['title'] = ''
            i['img_url'] = item['picture_small']
            i['album'] = ''
            i['album_id'] = ''
            i['artist'] = item['name']
            i['artist_id'] = item['id']
            i['preview_url'] = ''
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


def get_deezer_favorites(user_id: str) -> Optional[Sequence[int]]:
    if not user_id.isnumeric():
        raise Exception(f"User id '{user_id}' must be numeric")
    resp = session.get(f"https://api.deezer.com/user/{user_id}/tracks?limit=10000000000")
    assert resp.status_code == 200, f"got invalid status asking for favorite song\n{resp.text}s"
    resp_json = resp.json()
    if "error" in resp_json.keys():
        raise Exception(f"Upstream api error getting favorite songs for user {user_id}:\n{resp_json['error']}")
    # check is set next

    while "next" in resp_json.keys():
        resp = session.get(resp_json["next"])
        assert resp.status_code == 200, f"got invalid status asking for favorite song\n{resp.text}s"
        resp_json_next = resp.json()
        if "error" in resp_json_next.keys():
            raise Exception(f"Upstream api error getting favorite songs for user {user_id}:\n{resp_json_next['error']}")
        resp_json["data"] += resp_json_next["data"]

        if "next" in resp_json_next.keys():
            resp_json["next"] = resp_json_next["next"]
        else:
            del resp_json["next"]

    print(f"Got {resp_json['total']} favorite songs for user {user_id} from the api")
    songs = [song['id'] for song in resp_json['data']]
    return songs


def test_deezer_login():
    print("Let's check if the deezer login is still working")
    try:
        song = get_song_infos_from_deezer_website(TYPE_TRACK, "917265")
    except (Deezer403Exception, Deezer404Exception) as msg:
        print(msg)
        print("Login is not working anymore.")
        return False

    if song:
        print("Login is still working.")
        return True
    else:
        print("Login is not working anymore.")
        return False


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "check-login":
        test_deezer_login()
