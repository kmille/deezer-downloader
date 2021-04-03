import re
from time import sleep
from urllib.parse import urlparse, parse_qs

import requests

token_url = 'https://open.spotify.com/get_access_token?reason=transport&productType=web_player'
playlist_base_url = 'https://api.spotify.com/v1/playlists/{}/tracks?limit=100&additional_types=track&market=GB'  # todo figure out market
track_base_url = 'https://api.spotify.com/v1/tracks/{}'
album_base_url = 'https://api.spotify.com/v1/albums/{}/tracks'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'}


class SpotifyInvalidUrlException(Exception):
    pass


class SpotifyWebsiteParserException(Exception):
    pass


def parse_uri(uri):
    u = urlparse(uri)
    if u.netloc == "embed.spotify.com":
        if not u.query:
            raise SpotifyInvalidUrlException("ERROR: url {} is not supported".format(uri))

        qs = parse_qs(u.query)
        return parse_uri(qs['uri'][0])

    # backwards compatibility
    if not u.scheme and not u.netloc:
        return {"type": "playlist", "id": u.path}

    if u.scheme == "spotify":
        parts = uri.split(":")
    else:
        if u.netloc != "open.spotify.com" and u.netloc != "play.spotify.com":
            raise SpotifyInvalidUrlException("ERROR: url {} is not supported".format(uri))

        parts = u.path.split("/")

    if parts[1] == "embed":
        parts = parts[1:]

    l = len(parts)
    if l == 3 and parts[1] in ["album", "track", "playlist"]:
        return {"type": parts[1], "id": parts[2]}
    if l == 5 and parts[3] == "playlist":
        return {"type": parts[3], "id": parts[4]}

    # todo add support for other types; artists, searches, users

    raise SpotifyInvalidUrlException("ERROR: unable to determine Spotify URL type or type is unsupported.")


def get_songs_from_spotify_website(playlist):
    # parses Spotify Playlist from Spotify website
    # playlist: playlist url or playlist id as string
    # e.g. https://open.spotify.com/playlist/0wl9Q3oedquNlBAJ4MGZtS
    # e.g. https://open.spotify.com/embed/0wl9Q3oedquNlBAJ4MGZtS
    # e.g. 0wl9Q3oedquNlBAJ4MGZtS
    # return: list of songs (song: artist - title)
    # raises SpotifyWebsiteParserException if parsing the website goes wrong

    return_data = []
    url_info = parse_uri(playlist)

    req = requests.get(token_url)
    if req.status_code != 200:
        raise SpotifyWebsiteParserException(
            "ERROR: {} gave us not a 200. Instead: {}".format(token_url, req.status_code))
    token = req.json()

    if url_info['type'] == "playlist":
        url = playlist_base_url.format(url_info["id"])
        while True:
            resp = get_json_from_api(url, token["accessToken"])
            for track in resp['items']:
                return_data.append(parse_track(track["track"]))

            if resp['next'] is None:
                break
            url = resp['next']
    elif url_info["type"] == "track":
        resp = get_json_from_api(track_base_url.format(url_info["id"]), token["accessToken"])
        if resp is None:  # try again in case of rate limit
            resp = get_json_from_api(track_base_url.format(url_info["id"]), token["accessToken"])

        return_data.append(parse_track(resp))
    elif url_info["type"] == "album":
        resp = get_json_from_api(album_base_url.format(url_info["id"]), token["accessToken"])
        if resp is None:  # try again in case of rate limit
            resp = get_json_from_api(album_base_url.format(url_info["id"]), token["accessToken"])

        for track in resp['items']:
            return_data.append(parse_track(track))

    return [track for track in return_data if track]


def parse_track(track):
    artist = track['artists'][0]['name']
    song = track['name']
    full = "{} {}".format(artist, song)
    # remove everything in brackets to get better search results later on Deezer
    # e.g. (Radio  Version) or (Remastered)
    return re.sub(r'\([^)]*\)', '', full)


def get_json_from_api(api_url, access_token):
    req = requests.get(api_url, headers={'Authorization': 'Bearer {}'.format(access_token)})

    if req.status_code == 429:
        seconds = int(req.headers.get("Retry-After")) + 1
        print("INFO: rate limited! Sleeping for {} seconds".format(seconds))
        sleep(seconds)
        return None

    if req.status_code != 200:
        raise SpotifyWebsiteParserException("ERROR: {} gave us not a 200. Instead: {}".format(api_url, req.status_code))
    return req.json()


if __name__ == '__main__':
    # playlist = "21wZXvtrERELL0bVtKtuUh"
    playlist = "0wl9Q3oedquNlBAJ4MGZtS"
    album = "spotify:album:7zCODUHkfuRxsUjtuzNqbd"
    song = "https://open.spotify.com/track/6piFKF6WvM6ZZLmi2Vz8Vt"
    print(get_songs_from_spotify_website(playlist))
