import os
import unittest
import pytest
from pathlib import Path
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen import MutagenError

from deezer_downloader.configuration import load_config

if "DEEZER_DOWNLOADER_CONFIG_FILE" in os.environ:
    config_file = Path(os.environ["DEEZER_DOWNLOADER_CONFIG_FILE"])
else:
    config_file = (Path(__file__).parents[1] / Path("deezer_downloader") / Path("cli") / Path("deezer-downloader.ini.template")).resolve()

load_config(config_file)
from deezer_downloader.configuration import config

from deezer_downloader.deezer import init_deezer_session, TYPE_TRACK, TYPE_ALBUM
from deezer_downloader.deezer import deezer_search, get_song_infos_from_deezer_website, parse_deezer_playlist, download_song, get_deezer_favorites
from deezer_downloader.deezer import Deezer404Exception, DeezerApiException
from deezer_downloader.spotify import get_songs_from_spotify_website, SpotifyWebsiteParserException, parse_uri, SpotifyInvalidUrlException
from deezer_downloader.youtubedl import youtubedl_download, YoutubeDLFailedException, DownloadedFileNotFoundException

known_song_keys = ["SNG_ID", "DURATION", "MD5_ORIGIN", "SNG_TITLE", "TRACK_NUMBER",
                   "ALB_PICTURE", "MEDIA_VERSION", "ART_NAME", "ALB_TITLE"]

init_deezer_session(config['proxy']['server'],
                    config["deezer"]["quality"])


class TestDeezerMethods(unittest.TestCase):

    # BEGIN: TEST deezer_search
    def test_deezer_search_song_valid(self):
        songs = deezer_search("Großstadtgeflüster diadem", TYPE_TRACK)
        self.assertIsInstance(songs, list)
        s = songs[0]
        self.assertSetEqual(set(s.keys()), {'preview_url', 'artist', 'id', 'id_type', 'album_id', 'title', 'img_url', 'album'})
        self.assertTrue(s['id'], '730393272')
        self.assertTrue(s['title'], 'Diadem')
        self.assertTrue(s['artist'], 'Grossstadtgeflüster')
        self.assertTrue(s['album'], 'Tips & Tricks')
        self.assertTrue(s['preview_url'], 'https://cdns-preview-6.dzcdn.net/stream/c-6abdd540dd7e7f02d2c4d21537709c23-3.mp3')
        self.assertTrue(s['album_id'], '107261872')
        self.assertTrue(s['id_type'], 'track')

    def test_deezer_search_album_valid(self):
        albums = deezer_search("Coldplay", TYPE_ALBUM)
        self.assertIsInstance(albums, list)
        for album in albums:
            self.assertSetEqual(set(album.keys()), {'id', 'id_type', 'album', 'album_id', 'img_url', 'artist', 'title', 'preview_url'})

        found_album_names = [x['album'] for x in albums]
        known_album_names = ['Parachutes', 'X&Y', 'A Head Full of Dreams']
        for known_album_name in known_album_names:
            self.assertIn(known_album_name, found_album_names)

    def test_deezer_search_invalid_search_typ(self):
        songs = deezer_search("Coldplay", "this is a wrong search type")
        self.assertIsInstance(songs, list)
        self.assertListEqual(songs, [])

    def test_deezer_search_song_invalid_no_song_found(self):
        songs = deezer_search("8f49834zf934fdshfkhejw", TYPE_TRACK)
        self.assertIsInstance(songs, list)
        self.assertListEqual(songs, [])

    def test_deezer_search_album_invalid_no_song_found(self):
        songs = deezer_search("8f49834zf934fdshfkhejw", TYPE_ALBUM)
        self.assertIsInstance(songs, list)
        self.assertListEqual(songs, [])
    # END: TEST deezer_search

    # BEGIN: TEST get_song_infos_from_deezer_website
    def test_get_track_infos_from_website(self):
        song = get_song_infos_from_deezer_website(TYPE_TRACK, "69962764")
        self.assertIsInstance(song, dict)
        song_keys = list(song.keys())
        for key in known_song_keys:
            self.assertIn(key, song_keys)
        self.assertEqual(song["SNG_ID"], "69962764")
        self.assertEqual(song["ART_NAME"], "The Clash")
        self.assertEqual(song["SNG_TITLE"], "Should I Stay or Should I Go")
        # MD5_ORIGIN changes over time
        #self.assertEqual(song["MD5_ORIGIN"], "df51967a8b9b88d079fb0d9f4a0c1c38")
        self.assertEqual(len(song["MD5_ORIGIN"]), 32)

    def test_get_album_infos_from_website(self):
        songs = get_song_infos_from_deezer_website(TYPE_ALBUM, "1434890")
        self.assertIsInstance(songs, list)
        self.assertEqual(len(songs), 15)
        for song in songs:
            song_keys = list(song.keys())
            for key in known_song_keys:
                self.assertIn(key, song_keys)
        self.assertEqual(songs[0]["SNG_ID"], "15523769")
        self.assertEqual(songs[0]["ART_NAME"], "System of A Down")
        self.assertEqual(songs[0]["SNG_TITLE"], "Prison Song")
        self.assertEqual(len(songs[14]["MD5_ORIGIN"]), 32)
        self.assertEqual(songs[1]["SNG_ID"], "15523770")
        self.assertEqual(songs[1]["ART_NAME"], "System of A Down")
        self.assertEqual(songs[1]["SNG_TITLE"], "Needles")
        self.assertEqual(songs[2]["SNG_ID"], "15523772")
        self.assertEqual(songs[2]["ART_NAME"], "System of A Down")
        self.assertEqual(songs[2]["SNG_TITLE"], "Deer Dance")
        self.assertEqual(songs[3]["SNG_ID"], "15523775")
        self.assertEqual(songs[3]["ART_NAME"], "System of A Down")
        self.assertEqual(songs[3]["SNG_TITLE"], "Jet Pilot")
        self.assertEqual(songs[4]["SNG_ID"], "15523778")
        self.assertEqual(songs[4]["ART_NAME"], "System of A Down")
        self.assertEqual(songs[4]["SNG_TITLE"], "X")
        self.assertEqual(songs[5]["SNG_ID"], "15523781")
        self.assertEqual(songs[5]["ART_NAME"], "System of A Down")
        self.assertEqual(songs[5]["SNG_TITLE"], "Chop Suey!")
        self.assertEqual(songs[6]["SNG_ID"], "15523784")
        self.assertEqual(songs[6]["ART_NAME"], "System of A Down")
        self.assertEqual(songs[6]["SNG_TITLE"], "Bounce")
        self.assertEqual(songs[7]["SNG_ID"], "15523788")
        self.assertEqual(songs[7]["ART_NAME"], "System of A Down")
        self.assertEqual(songs[7]["SNG_TITLE"], "Forest")
        self.assertEqual(songs[8]["SNG_ID"], "15523790")
        self.assertEqual(songs[8]["ART_NAME"], "System of A Down")
        self.assertEqual(songs[8]["SNG_TITLE"], "ATWA")
        self.assertEqual(songs[9]["SNG_ID"], "15523791")
        self.assertEqual(songs[9]["ART_NAME"], "System of A Down")
        self.assertEqual(songs[9]["SNG_TITLE"], "Science")
        self.assertEqual(songs[10]["SNG_ID"], "15523792")
        self.assertEqual(songs[10]["ART_NAME"], "System of A Down")
        self.assertEqual(songs[10]["SNG_TITLE"], "Shimmy")
        self.assertEqual(songs[11]["SNG_ID"], "15523793")
        self.assertEqual(songs[11]["ART_NAME"], "System of A Down")
        self.assertEqual(songs[11]["SNG_TITLE"], "Toxicity")
        self.assertEqual(songs[12]["SNG_ID"], "15523796")
        self.assertEqual(songs[12]["ART_NAME"], "System of A Down")
        self.assertEqual(songs[12]["SNG_TITLE"], "Psycho")
        self.assertEqual(songs[13]["SNG_ID"], "15523799")
        self.assertEqual(songs[13]["ART_NAME"], "System of A Down")
        self.assertEqual(songs[13]["SNG_TITLE"], "Aerials")
        self.assertEqual(songs[14]["SNG_ID"], "15523803")
        self.assertEqual(songs[14]["ART_NAME"], "System of A Down")
        self.assertEqual(songs[14]["SNG_TITLE"], "Arto")

    def test_get_invalid_track_infos_from_website(self):
        with self.assertRaises(Deezer404Exception):
            get_song_infos_from_deezer_website(TYPE_TRACK, "thisdoesnotexist")

    def test_get_invalid_album_infos_from_website(self):
        with self.assertRaises(Deezer404Exception):
            get_song_infos_from_deezer_website(TYPE_ALBUM, "thisdoesnotexist")
    # END: TEST get_song_infos_from_deezer_website

    # BEGIN: parse_deezer_playlist
    def _call_parse_valid_deezer_playlist(self, playlist):
        playlist_name, songs = parse_deezer_playlist(playlist)
        self.assertEqual(playlist_name, "test-playlist")
        self.assertIsInstance(songs, list)
        self.assertEqual(len(songs), 2)
        for song in songs:
            song_keys = list(song.keys())
            for key in known_song_keys:
                self.assertIn(key, song_keys)
        self.assertEqual(songs[0]["SNG_ID"], "113951680")
        self.assertEqual(songs[0]["ART_NAME"], 'Fredrika Stahl')
        self.assertEqual(songs[0]["SNG_TITLE"], 'Make a Change')
        # MD5_ORIGIN is only there if we are logged in
        self.assertEqual(songs[0]["MD5_ORIGIN"], '57250623592ef44c8caeead79917f7e5')

    def test_parse_valid_deezer_playlist_with_url(self):
        playlist_url = "https://www.deezer.com/de/playlist/7639370122"
        self._call_parse_valid_deezer_playlist(playlist_url)

    def test_parse_valid_deezer_playlist_with_id(self):
        playlist_id = "7639370122"
        self._call_parse_valid_deezer_playlist(playlist_id)

    def test_parse_invalid_deezer_playlist_with_id(self):
        invalid_playlist_id = "999999999999999999999999999"
        with self.assertRaises(DeezerApiException):
            playlist_name, songs = parse_deezer_playlist(invalid_playlist_id)

    def test_parse_invalid_input_for_deezer_playlist_with_id(self):
        invalid_playlist_id = "!\"§$%&/((;-';k(()=+ü\\?"
        with self.assertRaises(DeezerApiException):
            playlist_name, songs = parse_deezer_playlist(invalid_playlist_id)

    def test_parse_invalid_deezer_playlist_with_url(self):
        invalid_playlist_url = "https://www.heise.de"
        with self.assertRaises(DeezerApiException):
            playlist_name, songs = parse_deezer_playlist(invalid_playlist_url)
    # END: parse_deezer_playlist

    # BEGIN: get_deezer_favorites
    def test_get_deezer_favorites_userid_not_numeric(self):
        user_id = "123notnumeric"
        with self.assertRaises(Exception):
            get_deezer_favorites(user_id)

    def test_get_deezer_favorites_userid_api_error(self):
        user_id = "0"
        with self.assertRaises(Exception):
            get_deezer_favorites(user_id)

    def test_get_deezer_favorites_userid_valid(self):
        user_id = "2517244282" # own of test (works)
        songs = get_deezer_favorites(user_id)
        self.assertIsInstance(songs, list)
        for song in songs:
            self.assertIsInstance(song, int)
    # END: get_deezer_favorites

    # BEGIN: download_song
    @pytest.mark.skipif(config["deezer"].get("quality", "mp3") == "flac", reason="skiping deezer mp3 download. Quality set to flac")
    def test_download_song_valid_mp3(self):
        def check_mp3_metadata_deezer_song(test_file: Path):
            self.assertTrue(test_song.exists())
            try:
                audio = MP3(test_file)
            except MutagenError as e:
                pytest.fail(f"File is not in mp3 format: {e}")
            self.assertEqual(audio['TPE1'].text[0], 'Faber')
            self.assertEqual(audio['TALB'].text[0], 'Alles Gute')
            self.assertEqual(audio['TIT2'].text[0], 'Tausendfrankenlang')
            self.assertEqual(audio['TRCK'].text[0], '4')
            self.assertEqual(audio['TDRC'].text[0].year, 2015)
            self.assertEqual(audio['TPOS'].text[0], '1')
            self.assertTrue('APIC:Cover' in audio)

        test_song = Path("/tmp/song-548935.mp3")
        test_song.unlink(missing_ok=True)

        song_infos = deezer_search("faber tausendfrankenlang", TYPE_TRACK)[0]
        song = get_song_infos_from_deezer_website(TYPE_TRACK, song_infos['id'])
        download_song(song, test_song.as_posix())
        check_mp3_metadata_deezer_song(test_song)
        test_song.unlink()

    @pytest.mark.skipif(config["deezer"].get("quality", "mp3") == "mp3", reason="skiping deezer flac download. Quality set to mp3")
    def test_download_song_valid_flac(self):
        def check_flac_metadata_deezer_song(test_file: Path):
            try:
                audio = FLAC(test_file)
            except MutagenError as e:
                pytest.fail(f"File is not in mp3 format: {e}")

            assert audio["artist"] == ["Faber",]
            assert audio["title"] == ['Tausendfrankenlang',]
            assert audio["album"] == ['Alles Gute',]
            assert audio["tracknumber"] == ['4',]
            assert audio["discnumber"] == ["1",]
            assert len(audio.pictures) == 1
            assert audio.pictures[0].data[:5] == b'\xff\xd8\xff\xe0\x00'

        test_song = Path("/tmp/song-548935.flac")
        test_song.unlink(missing_ok=True)

        song_infos = deezer_search("faber tausendfrankenlang", TYPE_TRACK)[0]
        song = get_song_infos_from_deezer_website(TYPE_TRACK, song_infos['id'])
        download_song(song, test_song.as_posix())
        check_flac_metadata_deezer_song(test_song)
        test_song.unlink()

    def test_download_song_invalid_song_type(self):
        with self.assertRaises(AssertionError):
            download_song("this sould be a dict", "/not/relevant/outputfile.mp3")
    # END: download_song


class TestSpotifyMethods(unittest.TestCase):
    # BEGIN parse_uri
    def test_parse_url_spotify(self):
        res = parse_uri("spotify:album:Hksdhfaif23ffushef9823")
        self.assertEqual(res['type'], "album")
        self.assertEqual(res['id'], "Hksdhfaif23ffushef9823")

        res = parse_uri("spotify:playlist:Hksdhfaif23ffushef9823")
        self.assertEqual(res['type'], "playlist")
        self.assertEqual(res['id'], "Hksdhfaif23ffushef9823")

        res = parse_uri("spotify:track:Hksdhfaif23ffushef9823")
        self.assertEqual(res['type'], "track")
        self.assertEqual(res['id'], "Hksdhfaif23ffushef9823")

    def test_parse_url_open_domain(self):
        res = parse_uri("https://open.spotify.com/track/Hksdhfaif23ffushef9823")
        self.assertEqual(res['type'], "track")
        self.assertEqual(res['id'], "Hksdhfaif23ffushef9823")

    def test_parse_url_play_domain(self):
        res = parse_uri("https://play.spotify.com/track/Hksdhfaif23ffushef9823")
        self.assertEqual(res['type'], "track")
        self.assertEqual(res['id'], "Hksdhfaif23ffushef9823")

    def test_parse_url_embed_domain(self):
        res = parse_uri("https://embed.spotify.com/?uri=spotify:track:Hksdhfaif23ffushef9823")
        self.assertEqual(res['type'], "track")
        self.assertEqual(res['id'], "Hksdhfaif23ffushef9823")
    # END parse_uri

    # BEGIN test invalid
    @pytest.mark.skip(reason="Spotify API is currently not stable and not supported, see #174#issuecomment-3895518439")
    def test_spotify_parser_invalid_playlist_id(self):
        playlist_id = "thisdoesnotexist"
        with self.assertRaises(SpotifyWebsiteParserException):
            get_songs_from_spotify_website(playlist_id, None)

    def test_spotify_parser_invalid_playlist_url(self):
        playlist_url = "https://www.heise.de"
        with self.assertRaises(SpotifyInvalidUrlException):
            get_songs_from_spotify_website(playlist_url, None)
    # END test invalid

    # BEGIN valid stuff
    @pytest.mark.skip(reason="Spotify API is currently not stable and not supported, see #174#issuecomment-3895518439")
    def check_parse_spotify_playlist_website(self, playlist):
        songs = get_songs_from_spotify_website(playlist, None)
        self.assertIn("Cyndi Lauper Time After Time", songs)

    @pytest.mark.skip(reason="Spotify API is currently not stable and not supported, see #174#issuecomment-3895518439")
    def test_spotify_parser_valid_playlist_embed_url(self):
        playlist_url = "https://open.spotify.com/embed/playlist/0wl9Q3oedquNlBAJ4MGZtS"
        self.check_parse_spotify_playlist_website(playlist_url)

    @pytest.mark.skip(reason="Spotify API is currently not stable and not supported, see #174#issuecomment-3895518439")
    def test_spotify_parser_valid_playlist_url(self):
        playlist_url = "https://open.spotify.com/playlist/0wl9Q3oedquNlBAJ4MGZtS"
        self.check_parse_spotify_playlist_website(playlist_url)

    @pytest.mark.skip(reason="Spotify API is currently not stable and not supported, see #174#issuecomment-3895518439")
    def test_spotify_parser_valid_playlist_id(self):
        playlist_id = "0wl9Q3oedquNlBAJ4MGZtS"
        self.check_parse_spotify_playlist_website(playlist_id)
    # END valid stuff


class TestYoutubeMethods(unittest.TestCase):
    is_github_ci = len(os.environ.get("GITHUB_ACTION", "")) > 0

    @pytest.mark.xfail(is_github_ci, reason="Fails with 'Sign in to confirm you’re not a bot. This helps protect our community. Learn more'", raises=YoutubeDLFailedException)
    def test_youtube_dl_valid_url(self):
        out_file = Path("/tmp/Pharrell Williams - Happy (Official Video).mp3")
        out_file.unlink(missing_ok=True)
        url = "https://www.youtube.com/watch?v=ZbZSe6N_BXs"
        destination_file = youtubedl_download(url, "/tmp")
        self.assertEqual(out_file.as_posix(), destination_file)
        self.assertTrue(out_file.exists())
        try:
            audio = MP3(out_file)
            self.assertEqual(audio['TPE1'].text[0], 'Pharrell Williams')
            self.assertEqual(audio['TIT2'].text[0], 'Pharrell Williams - Happy (Official Video)')
        except MutagenError as e:
            pytest.fail(f"File is not in mp3 format: {e}")
        out_file.unlink()

    def test_youtube_dl_invalid_url(self):
        url = "https://www.heise.de"
        with self.assertRaises(YoutubeDLFailedException):
            youtubedl_download(url, "/tmp")

    @pytest.mark.xfail(is_github_ci, reason="Fails with 'Sign in to confirm you’re not a bot. This helps protect our community. Learn more'", raises=YoutubeDLFailedException)
    def test_youtube_dl_command_execution(self):
        url = "https://www.youtube.com/watch?v=ZbZSe6N_BXs&$(touch /tmp/pwned.txt)"
        try:
            youtubedl_download(url, "/tmp")
        except DownloadedFileNotFoundException:
            pytest.xfail("Fails if the file already exists from the previous test. TODO")
        pwn_succeeded = os.path.exists("/tmp/pwned.txt")
        self.assertEqual(pwn_succeeded, False)


if __name__ == '__main__':
    unittest.main()
