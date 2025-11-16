import pytest
from deezer_downloader import deezer
import re
import json
import struct
import urllib.parse
import html.parser
import requests
import io
from binascii import a2b_hex, b2a_hex
from Crypto.Cipher import Blowfish
from Crypto.Hash import MD5

# No additional imports needed beyond what already exist in the test file.
# No additional imports needed beyond what already exist in the test file.
def test_calcbfkey_known_value():
    """
    Test that calcbfkey returns the expected Blowfish decryption key 
    for a known song id ('123456'). This increases coverage for the crypto helper function.
    """
    # The MD5 hash of "123456" is "e10adc3949ba59abbe56e057f20f883e".
    # Then, calcbfkey computes the key by XORing each character of the first 16 characters
    # with the corresponding character in the last 16 characters and the static key b"g4el58wc0zvf9na1".
    # The expected result from these operations is "
def test_get_song_infos_not_logged_in(monkeypatch):
    """
    Test that get_song_infos_from_deezer_website raises Deezer403Exception
    when the response from Deezer does not contain the expected "MD5_ORIGIN"
    (simulating a situation where we are not logged in).
    """
    # Define a dummy response that does not contain "MD5_ORIGIN"
    class DummyResponse:
        def __init__(self, status_code, text):
            self.status_code = status_code
            self.text = text
        def raise_for_status(self):
            # Assume response is OK so do nothing
            pass
    # Define a dummy session where get() returns our dummy response
    class DummySession:
        def get(self, url):
            # Returning a page without "MD5_ORIGIN"
            return DummyResponse(200, "<html><head></head><body>Not logged in</body></html>")
    # Monkeypatch the global session in the deezer module
    monkeypatch.setattr(deezer, "session", DummySession())
    # This call should raise a Deezer403Exception because "MD5_ORIGIN" is missing.
    with pytest.raises(deezer.Deezer403Exception) as excinfo:
        deezer.get_song_infos_from_deezer_website(deezer.TYPE_TRACK, "dummy_id")
    
    # Optionally, check that the exception message mentions login issues.
    assert "not logged in" in str(excinfo.value).lower()
def test_downloadpicture_returns_dummy_content(monkeypatch):
    """
    Test that downloadpicture returns the expected dummy image content.
    This test monkeypatches the session.get method to simulate a network response.
    """
    dummy_content = b"dummyimage"
    
    class DummyResponse:
        def __init__(self, content):
            self.content = content
    class DummySession:
        def get(self, url):
            # Verify that the URL is constructed correctly for a cover image.
            assert "cover" in url
            return DummyResponse(dummy_content)
    # Monkeypatch the global session in the deezer module with our dummy session.
    monkeypatch.setattr(deezer, "session", DummySession())
    
    # Call downloadpicture and verify that it returns the dummy content.
    result = deezer.downloadpicture("dummy_pic_id")
    assert result == dummy_content
def test_writeid3v1_tag_creates_tag():
    """
    Test that writeid3v1_1 writes an ID3v1.1 tag that starts with the 'TAG' header
    and that the tag length matches the expected size.
    """
    # Create a dummy song dictionary with necessary keys
    dummy_song = {
        "SNG_TITLE": "Test Song",
        "ART_NAME": "Test Artist",
        "ALB_TITLE": "Test Album",
        "TRACK_NUMBER": "1"
    }
    # Set the global album_Data variable with dummy values required by album_get
    deezer.album_Data = {
        "PHYSICAL_RELEASE_DATE": "2020",
        "LABEL_NAME": "Test Label",
        "TRACKS": "10"
    }
    # Use BytesIO to capture the output written by writeid3v1_1
    output_file = io.BytesIO()
    deezer.writeid3v1_1(output_file, dummy_song)
    result = output_file.getvalue()
    # Check that the tag starts with the "TAG" header (first 3 bytes)
    assert result.startswith(b"TAG")
    # Calculate expected size using the same struct format used in writeid3v1_1:
    # The format string is "3s30s30s30s4s28sBHB" (combining the pieces from the code)
    expected_size = struct.calcsize("3s30s30s30s4s28sBHB")
    # Check that the written tag length equals the expected size
    assert len(result) == expected_size
def test_set_song_quality(monkeypatch, capsys):
    """
    Test that set_song_quality correctly sets the global sound_format:
    - When lossless is supported and quality_config is "flac", it should set sound_format to "FLAC".
    - When lossless is not supported, it should fallback to "MP3_128" and print a warning.
    """
    # Case 1: flac quality_config and premium lossless support => should set to FLAC.
    deezer.set_song_quality("flac", {"lossless": True})
    assert deezer.sound_format == "FLAC", "Expected sound_format to be FLAC when lossless is supported."
    # Case 2: flac quality_config but lossless not supported => should fallback to MP3_128 and print warning.
    deezer.set_song_quality("flac", {"lossless": False})
    assert deezer.sound_format == "MP3_128", "Expected sound_format to fallback to MP3_128 when lossless is not supported."
    captured = capsys.readouterr().out
    assert "WARNING: flac quality is configured" in captured, "Expected a warning message when flac is not supported."
def test_parse_deezer_playlist_returns_playlist_data(monkeypatch):
    """
    Test that parse_deezer_playlist correctly processes a dummy API response and returns the expected
    playlist name and list of songs.
    """
    class DummyResponse:
        def __init__(self, json_data):
            self._json = json_data
            self.status_code = 200
        def json(self):
            return self._json
    class DummySession:
        def post(self, url, json=None):
            if "method=deezer.getUserData" in url:
                # Simulate CSRF token retrieval
                return DummyResponse({"results": {"checkForm": "dummycsrf"}})
            elif "method=deezer.pagePlaylist" in url:
                # Simulate playlist request returning dummy data
                return DummyResponse({
                    "error": "",
                    "results": {
                        "DATA": {"TITLE": "My Playlist", "NB_SONG": 2},
                        "SONGS": {"count": 2, "data": [
                            {"SNG_ID": "1", "SNG_TITLE": "Song1"},
                            {"SNG_ID": "2", "SNG_TITLE": "Song2"}
                        ]}
                    }
                })
            else:
                return DummyResponse({})
    
    # Monkeypatch the global session with DummySession
    monkeypatch.setattr(deezer, "session", DummySession())
    
    # Call parse_deezer_playlist with a dummy playlist_id (digits will be extracted)
    playlist_name, songs = deezer.parse_deezer_playlist("12345")
    
    # Assert that the response matches our dummy data
    assert playlist_name == "My Playlist"
    assert isinstance(songs, list)
    assert len(songs) == 2
    assert songs[0]["SNG_ID"] == "1"
    assert songs[0]["SNG_TITLE"] == "Song1"
    assert songs[1]["SNG_ID"] == "2"
    assert songs[1]["SNG_TITLE"] == "Song2"
def test_blowfish_decrypt_returns_original():
    """
    Test that blowfishDecrypt correctly decrypts ciphertext produced by Blowfish encryption.
    This increases test coverage for the crypto helper function by ensuring that encryption/decryption
    with the fixed IV and key returns the original data.
    """
    # Use the same key as the decryption function expects
    key = "g4el58wc0zvf9na1"
    # The initialization vector as a hex string used in blowfishDecrypt: "0001020304050607"
    iv = a2b_hex("0001020304050607")
    # Prepare a plaintext block that is exactly 8 bytes (Blowfish block size)
    plaintext = b"ABCDEFGH"
    # Create a Blowfish cipher with the same key and IV, using CBC mode
    cipher = Blowfish.new(key.encode(), Blowfish.MODE_CBC, iv)
    # Encrypt the plaintext to obtain ciphertext
    ciphertext = cipher.encrypt(plaintext)
    # Now use the function under test to decrypt the ciphertext
    decrypted = deezer.blowfishDecrypt(ciphertext, key)
    # Verify that the decrypted text matches the original plaintext
    assert decrypted == plaintext
def test_script_extractor_extracts_scripts():
    """
    Test that ScriptExtractor correctly extracts all script contents from HTML with multiple <script> tags.
    """
    # Create a dummy HTML with two script tags.
    html_input = (
        '<html>'
        '<head><script>console.log("Hello")</script></head>'
        '<body>'
        '<script>var a = 1;</script>'
        '<div>Not a script</div>'
        '<script>\nalert("Test");\n</script>'
        '</body>'
        '</html>'
    )
    # Initialize the ScriptExtractor from the original source code.
    parser = deezer.ScriptExtractor()
    parser.feed(html_input)
    parser.close()
    
    # We expect the parser to extract the content of all three script tags.
    expected_scripts = [
        'console.log("Hello")',
        'var a = 1;',
        '\nalert("Test");\n'
    ]
    assert parser.scripts == expected_scripts, "Extracted scripts do not match expected output."
def test_deezer_search_returns_expected_results(monkeypatch):
    """
    Test that deezer_search returns correctly formatted results for a search query.
    This test monkeypatches the 'session.get' method to simulate a dummy API response.
    """
    # Define a dummy response with a json() method returning dummy data.
    class DummyResponse:
        def __init__(self, json_data):
            self._json = json_data
            self.status_code = 200
        def json(self):
            return self._json
    # Define a dummy session with a get method that returns the dummy response.
    class DummySession:
        def get(self, url):
            # Check that the URL is constructed correctly for a search query.
            # For TYPE_TRACK, expect the URL to contain "/search/track?q="
            assert "search/track" in url, f"URL '{url}' does not contain expected segment."
            # Return dummy JSON that simulates one track.
            dummy_json = {
                "data": [{
                    "id": "1",
                    "title": "Dummy Song",
                    "album": {
                        "cover_small": "http://dummy.url/cover.jpg",
                        "title": "Dummy Album",
                        "id": "101"
                    },
                    "artist": {"name": "Dummy Artist"},
                    "preview": "http://dummy.url/preview.mp3"
                }]
            }
            return DummyResponse(dummy_json)
    # Monkeypatch the global session in the deezer module with our dummy session.
    monkeypatch.setattr(deezer, "session", DummySession())
    # Call the function under test with TYPE_TRACK and a dummy search term.
    results = deezer.deezer_search("dummy search", deezer.TYPE_TRACK)
    # Check that the result is a list with one track and that the keys match.
    assert isinstance(results, list), "Expected results to be a list."
    assert len(results) == 1, "Expected a single track in the search result."
    track = results[0]
    expected_keys = {"id", "id_type", "title", "img_url", "album", "album_id", "artist", "preview_url"}
    assert expected_keys.issubset(track.keys()), f"Missing keys in returned result. Expected at least: {expected_keys}"
    assert track["id"] == "1"
    assert track["title"] == "Dummy Song"
    assert track["img_url"] == "http://dummy.url/cover.jpg"
    assert track["album"] == "Dummy Album"
    assert track["album_id"] == "101"
    assert track["artist"] == "Dummy Artist"
    assert track["preview_url"] == "http://dummy.url/preview.mp3"
def test_get_song_url_api_error(monkeypatch):
    """
    Test that get_song_url raises a RuntimeError when the API returns an error response.
    This test simulates an API response containing an error message and verifies that
    the exception is raised with the expected message.
    """
    # Ensure the global license_token is set so that get_song_url can proceed.
    deezer.license_token = {"dummy": "dummy"}
    
    # Define a dummy response that simulates an API error response.
    class DummyResponse:
        def __init__(self):
            self.status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {"data": [{"errors": [{"message": "Test error from API"}]}]}
    
    # Define a dummy requests.post to return our DummyResponse.
    def dummy_post(*args, **kwargs):
        return DummyResponse()
    
    # Monkeypatch the requests.post function used in get_song_url.
    monkeypatch.setattr(requests, "post", dummy_post)
    
    # Verify that calling get_song_url raises a RuntimeError with the expected error message.
    with pytest.raises(RuntimeError, match="Test error from API"):
        deezer.get_song_url("dummy_track")