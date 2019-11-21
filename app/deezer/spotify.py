import requests
from bs4 import BeautifulSoup
import json
import re

#from deezer import deezerSearch, my_download_song
from ipdb import set_trace


base_url = "https://open.spotify.com/embed/playlist/{}"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'}


def get_songs_from_spotify_website(playlist_id):
    return_data = []
    if playlist_id.startswith("http"):
        url = playlist_id.replace("spotify.com/playlist", "spotify.com/embed/playlist")
    else:
        url = base_url.format(playlist_id)

    req = requests.get(url)
    if req.status_code != 200:
        print("ERROR: {} gave us not a 200. Instead: {}".format(url, req.status_code))
        return

    bs = BeautifulSoup(req.text, 'html.parser')
    try:
        songs_txt = bs.find('script', {'id': 'resource'}).text.strip()
    except AttributeError:
        print("ERROR: Could not get songs from Spotify website. Wrong Playlist id? Tried {}".format(url))
        return
    songs_json = json.loads(songs_txt)

    for track in songs_json['tracks']['items']:
        artist = track['track']['artists'][0]['name']
        song = track['track']['name']
        full = "{} {}".format(artist, song)
        # remove everything in brackets: (  +  'not )'*  +  )
        full = re.sub(r'\([^)]*\)', '', full)
        return_data.append(full)
    return return_data


def download_fqdn_song(artist_song, update_mpd, add_to_playlist):
    # we just take the first of the search
    try:
        song_to_download_dict = deezerSearch(artist_song, 'track')[0]
        my_download_song(song_to_download_dict['id'],
                         update_mpd=update_mpd,
                         add_to_playlist=add_to_playlist)
    except IndexError:
        print("Found no song for '{}'".format(artist_song))


if __name__ == '__main__':
    #playlist = "21wZXvtrERELL0bVtKtuUh"
    playlist = "0wl9Q3oedquNlBAJ4MGZtS?si=jmdvnQSyRYCxDTWzrZARJg"

    songs = parse_spotify_playlist(playlist)
    for song in songs:
        print(song)
        download_fqdn_song(song, False, False)
        #todo: put everything in a dedicated folder
