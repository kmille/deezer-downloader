import pytest
from deezer_downloader import spotify
from time import sleep

def test_get_json_rate_limit(monkeypatch, capsys):
    """
    Test get_json_from_api when the API returns a 429 rate limit response.
    This test verifies that the function prints the rate limiting message,
    sleeps for the designated time (patched to avoid delay), and returns None.
    """
    class FakeResponse:
        def __init__(self, status_code, headers):
            self.status_code = status_code
            self.headers = headers
        def json(self):
            return {}
    def fake_requests_get(url, headers, proxies):
        return FakeResponse(429, {"Retry-After": "1"})
    monkeypatch.setattr(spotify.requests, "get", fake_requests_get)
    monkeypatch.setattr(spotify, "sleep", lambda seconds: None)
    result = spotify.get_json_from_api("http://dummy_url", "dummy_token", proxy="dummy_proxy")
    output = capsys.readouterr().out
    assert "rate limited" in output
    assert result is None

def test_parse_uri_with_invalid_netloc():
    """
    Test parse_uri with a URL having an unsupported netloc.
    This should raise SpotifyInvalidUrlException since the URL's domain is not supported by the parser.
    """
    invalid_url = "https://www.example.com/playlist/12345"
    with pytest.raises(spotify.SpotifyInvalidUrlException):
        spotify.parse_uri(invalid_url)

def test_get_json_success(monkeypatch):
    """
    Test get_json_from_api when the API returns a 200 status code.
    This verifies that the function correctly returns the JSON response payload.
    """
    class FakeResponse:
        def __init__(self):
            self.status_code = 200
            self.headers = {}
        def json(self):
            return {"key": "value"}
    def fake_requests_get(url, headers, proxies):
        return FakeResponse()
    monkeypatch.setattr(spotify.requests, "get", fake_requests_get)
    result = spotify.get_json_from_api("http://dummy_url", "dummy_token", proxy="dummy_proxy")
    assert result == {"key": "value"}

def test_parse_uri_embed():
    """
    Test parse_uri with a Spotify embed URL.
    Verifies that an embed URL in the form "https://embed.spotify.com/?uri=spotify:track:..." 
    correctly returns the corresponding type and id.
    """
    embed_url = "https://embed.spotify.com/?uri=spotify:track:6piFKF6WvM6ZZLmi2Vz8Vt"
    expected = {"type": "track", "id": "6piFKF6WvM6ZZLmi2Vz8Vt"}
    result = spotify.parse_uri(embed_url)
    assert result == expected

def test_parse_uri_spotify_uri():
    """
    Test parse_uri with Spotify URIs in the format "spotify:<type>:<id>".
    This verifies that the parser correctly extracts the type and id for both album and track URIs.
    """
    album_uri = "spotify:album:7zCODUHkfuRxsUjtuzNqbd"
    expected_album = {"type": "album", "id": "7zCODUHkfuRxsUjtuzNqbd"}
    result_album = spotify.parse_uri(album_uri)
    assert result_album == expected_album

    track_uri = "spotify:track:6piFKF6WvM6ZZLmi2Vz8Vt"
    expected_track = {"type": "track", "id": "6piFKF6WvM6ZZLmi2Vz8Vt"}
    result_track = spotify.parse_uri(track_uri)
    assert result_track == expected_track

def test_get_songs_from_spotify_album(monkeypatch):
    """
    Test get_songs_from_spotify_website for album type.
    This test simulates the API's token endpoint and album endpoint responses.
    It verifies that the function correctly returns the list of parsed tracks from an album.
    """
    token_response = {"accessToken": "dummy_access_token"}
    album_response_data = {
        "items": [
            {"artists": [{"name": "Artist1"}], "name": "Song1 (Remastered)"},
            {"artists": [{"name": "Artist2"}], "name": "Song2"}
        ]
    }
    class FakeTokenResponse:
        def __init__(self):
            self.status_code = 200
            self.headers = {}
        def json(self):
            return token_response
    class FakeAlbumResponse:
        def __init__(self):
            self.status_code = 200
            self.headers = {}
        def json(self):
            return album_response_data
    def fake_requests_get(url, headers, proxies):
        if url == spotify.token_url:
            return FakeTokenResponse()
        elif url.startswith("https://api.spotify.com/v1/albums/"):
            return FakeAlbumResponse()
        else:
            raise ValueError("Unexpected URL: " + url)
    monkeypatch.setattr(spotify.requests, "get", fake_requests_get)
    album_uri = "spotify:album:7zCODUHkfuRxsUjtuzNqbd"
    tracks = spotify.get_songs_from_spotify_website(album_uri, proxy="dummy_proxy")
    expected_tracks = ["Artist1 Song1 ", "Artist2 Song2"]
    assert tracks == expected_tracks

def test_get_songs_from_spotify_playlist_pagination(monkeypatch):
    """
    Test get_songs_from_spotify_website for playlist pagination.
    This test simulates a playlist API response with two paginated pages.
    It verifies that the function collects and processes tracks from both pages.
    """
    class FakeResponse:
        def __init__(self, status_code, json_data, headers=None):
            self.status_code = status_code
            self._json = json_data
            self.headers = headers or {}
        def json(self):
            return self._json
    token_response = {"accessToken": "dummy_token"}
    playlist_page1 = {
        "items": [
            {"track": {"artists": [{"name": "Artist1"}], "name": "Song1 (Radio Edit)"}}
        ],
        "next": "http://dummy_next_page"
    }
    playlist_page2 = {
        "items": [
            {"track": {"artists": [{"name": "Artist2"}], "name": "Song2"}}
        ],
        "next": None
    }
    playlist_id = "dummy_playlist_id"
    first_page_url = spotify.playlist_base_url.format(playlist_id)
    def fake_requests_get(url, headers, proxies):
        if url == spotify.token_url:
            return FakeResponse(200, token_response)
        elif url == first_page_url:
            return FakeResponse(200, playlist_page1)
        elif url == "http://dummy_next_page":
            return FakeResponse(200, playlist_page2)
        else:
            raise ValueError("Unexpected URL: " + url)
    monkeypatch.setattr(spotify.requests, "get", fake_requests_get)
    tracks = spotify.get_songs_from_spotify_website(playlist_id, proxy="dummy_proxy")
    expected_tracks = ["Artist1 Song1 ", "Artist2 Song2"]
    assert tracks == expected_tracks

def test_get_songs_from_spotify_track(monkeypatch):
    """
    Test get_songs_from_spotify_website for track type.
    This test simulates the token API and track endpoint responses and verifies that
    a single track is correctly processed by the parser.
    """
    class FakeResponse:
        def __init__(self, status_code, json_data, headers=None):
            self.status_code = status_code
            self._json = json_data
            self.headers = headers or {}
        def json(self):
            return self._json
    token_response = {"accessToken": "dummy_access_token"}
    track_response = {"artists": [{"name": "TestArtist"}], "name": "TestSong (Live)"}
    def fake_requests_get(url, headers, proxies):
        if url == spotify.token_url:
            return FakeResponse(200, token_response)
        elif url == spotify.track_base_url.format("testtrackid"):
            return FakeResponse(200, track_response)
        else:
            raise ValueError("Unexpected URL: " + url)
    monkeypatch.setattr(spotify.requests, "get", fake_requests_get)
    track_uri = "spotify:track:testtrackid"
    tracks = spotify.get_songs_from_spotify_website(track_uri, proxy="dummy_proxy")
    expected_tracks = ["TestArtist TestSong "]
    assert tracks == expected_tracks

def test_get_songs_from_spotify_album_retry(monkeypatch):
    """
    Test get_songs_from_spotify_website for album type when the album endpoint first returns a 
    rate limiting response (429) and then succeeds upon retry. This test simulates the retry logic.
    """
    token_response = {"accessToken": "dummy_access_token"}
    album_response_data = {
        "items": [
            {"artists": [{"name": "ArtistRetry"}], "name": "SongRetry (Live)"}
        ]
    }
    call_counter = {"album_calls": 0}
    class FakeTokenResponse:
        def __init__(self):
            self.status_code = 200
            self.headers = {}
        def json(self):
            return token_response
    class FakeAlbumResponse:
        def __init__(self, status_code, json_data, headers=None):
            self.status_code = status_code
            self._json = json_data
            self.headers = headers or {}
        def json(self):
            return self._json
    def fake_requests_get(url, headers, proxies):
        if url == spotify.token_url:
            return FakeTokenResponse()
        elif url == spotify.album_base_url.format("retry_album_id"):
            if call_counter["album_calls"] == 0:
                call_counter["album_calls"] += 1
                return FakeAlbumResponse(429, {}, headers={"Retry-After": "1"})
            else:
                return FakeAlbumResponse(200, album_response_data)
        else:
            raise ValueError("Unexpected URL: " + url)
    monkeypatch.setattr(spotify.requests, "get", fake_requests_get)
    monkeypatch.setattr(spotify, "sleep", lambda seconds: None)
    album_uri = "spotify:album:retry_album_id"
    tracks = spotify.get_songs_from_spotify_website(album_uri, proxy="dummy_proxy")
    expected_tracks = ["ArtistRetry SongRetry "]
    assert tracks == expected_tracks

def test_parse_uri_backwards_compatibility():
    """
    Test parse_uri with a string that has no scheme and no netloc.
    This verifies the backwards compatibility branch where the input (a raw playlist id)
    is returned as a playlist type with the id equal to the original string.
    """
    simple_input = "simplePlaylistID"
    expected = {"type": "playlist", "id": "simplePlaylistID"}
    result = spotify.parse_uri(simple_input)
    assert result == expected
