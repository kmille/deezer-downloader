import requests
from bs4 import BeautifulSoup
import json
import re

base_url = "https://open.spotify.com/embed/playlist/{}"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'}


class SpotifyWebsiteParserException(Exception):
    pass


def get_songs_from_spotify_website(playlist):
    # parses Spotify Playlist from Spotify website
    # playlist: playlist url or playlist id as string
    # e.g. https://open.spotify.com/playlist/0wl9Q3oedquNlBAJ4MGZtS
    # e.g. https://open.spotify.com/embed/0wl9Q3oedquNlBAJ4MGZtS
    # e.g. 0wl9Q3oedquNlBAJ4MGZtS
    # return: list of songs (song: artist - title)
    # raises SpotifyWebsiteParserException if parsing the website goes wrong

    return_data = []
    if playlist.startswith("http"):
        url = playlist.replace("spotify.com/playlist", "spotify.com/embed/playlist")
    else:
        url = base_url.format(playlist)

    req = requests.get(url)
    if req.status_code != 200:
        raise SpotifyWebsiteParserException("ERROR: {} gave us not a 200. Instead: {}".format(url, req.status_code))

    bs = BeautifulSoup(req.text, 'html.parser')
    try:
        songs_txt = bs.find('script', {'id': 'resource'}).string.strip()
    except AttributeError:
        raise SpotifyWebsiteParserException("ERROR: Could not get songs from Spotify website. Wrong Playlist id? Tried {}".format(url))
    songs_json = json.loads(songs_txt)

    for track in songs_json['tracks']['items']:
        artist = track['track']['artists'][0]['name']
        song = track['track']['name']
        full = "{} {}".format(artist, song)
        # remove everything in brackets to get better search results later on Deezer
        # e.g. (Radio  Version) or (Remastered)
        full = re.sub(r'\([^)]*\)', '', full)
        return_data.append(full)
    return return_data


if __name__ == '__main__':
    #playlist = "21wZXvtrERELL0bVtKtuUh"
    playlist = "0wl9Q3oedquNlBAJ4MGZtS?si=jmdvnQSyRYCxDTWzrZARJg"
    get_songs_from_spotify_website(playlist)
