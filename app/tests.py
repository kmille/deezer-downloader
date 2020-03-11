import os
import unittest
import magic

from deezer import deezer_search, get_song_infos_from_deezer_website, parse_deezer_playlist, download_song
from deezer import TYPE_TRACK, TYPE_ALBUM
from deezer import Deezer404Exception, DeezerApiException
from spotify import get_songs_from_spotify_website, SpotifyWebsiteParserException
from youtubedl import youtubedl_download, YoutubeDLFailedException


from ipdb import set_trace

known_song_keys = ["SNG_ID", "DURATION", "MD5_ORIGIN", "SNG_TITLE", "TRACK_NUMBER",
                   "ALB_PICTURE", "MEDIA_VERSION", "ART_NAME", "ALB_TITLE"]
test_song = "/tmp/song-548935.mp3"


class TestDeezerMethods(unittest.TestCase):

    # BEGIN: TEST deezer_search
    def test_deezer_search_song_valid(self):
        songs = deezer_search("Großstadtgeflüster diadem", TYPE_TRACK)
        self.assertIsInstance(songs, list)
        s = songs[0]
        self.assertSetEqual(set(s.keys()), {'id', 'title', 'album', 'artist'})
        self.assertTrue(s['id'], '730393272')
        self.assertTrue(s['title'], 'Diadem')
        self.assertTrue(s['artist'], 'Grossstadtgeflüster')
        self.assertTrue(s['album'], 'Tips & Tricks')

    def test_deezer_search_album_valid(self):
        albums = deezer_search("Coldplay", TYPE_ALBUM)
        self.assertIsInstance(albums, list)
        for album in albums:
            self.assertSetEqual(set(album.keys()), {'id', 'title', 'album', 'artist'})

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
        self.assertEqual(song["MD5_ORIGIN"], "df51967a8b9b88d079fb0d9f4a0c1c38")

    def test_get_album_infos_from_website(self):
        songs = get_song_infos_from_deezer_website(TYPE_ALBUM, "1434890")
        self.assertIsInstance(songs, list)
        self.assertEqual(len(songs), 15)
        for song in songs:
            song_keys = list(song.keys())
            for key in known_song_keys:
                self.assertIn(key, song_keys)
        self.assertEqual(songs[0]["SNG_ID"], "15523769")
        self.assertEqual(songs[0]["ART_NAME"], "System of a Down")
        self.assertEqual(songs[0]["SNG_TITLE"], "Prison Song")
        self.assertEqual(songs[0]["MD5_ORIGIN"], "420dcfb48009fcbc806ba03397c1f651")
        self.assertEqual(songs[1]["SNG_ID"], "15523770")
        self.assertEqual(songs[1]["ART_NAME"], "System of a Down")
        self.assertEqual(songs[1]["SNG_TITLE"], "Needles")
        self.assertEqual(songs[1]["MD5_ORIGIN"], "19c32852ccef718fc5c6282f1d132e02")
        self.assertEqual(songs[2]["SNG_ID"], "15523772")
        self.assertEqual(songs[2]["ART_NAME"], "System of a Down")
        self.assertEqual(songs[2]["SNG_TITLE"], "Deer Dance")
        self.assertEqual(songs[2]["MD5_ORIGIN"], "ac8b7cb27c49613789ac006cbcdd154c")
        self.assertEqual(songs[3]["SNG_ID"], "15523775")
        self.assertEqual(songs[3]["ART_NAME"], "System of a Down")
        self.assertEqual(songs[3]["SNG_TITLE"], "Jet Pilot")
        self.assertEqual(songs[3]["MD5_ORIGIN"], "daff36398802a0d8a0b19b414e0e161f")
        self.assertEqual(songs[4]["SNG_ID"], "15523778")
        self.assertEqual(songs[4]["ART_NAME"], "System of a Down")
        self.assertEqual(songs[4]["SNG_TITLE"], "X")
        self.assertEqual(songs[4]["MD5_ORIGIN"], "f63415cdf261e4cf1af4373f1e06142c")
        self.assertEqual(songs[5]["SNG_ID"], "15523781")
        self.assertEqual(songs[5]["ART_NAME"], "System of a Down")
        self.assertEqual(songs[5]["SNG_TITLE"], "Chop Suey!")
        self.assertEqual(songs[5]["MD5_ORIGIN"], "2ea5a63b02e940e24fc8b0e66f5bee4a")
        self.assertEqual(songs[6]["SNG_ID"], "15523784")
        self.assertEqual(songs[6]["ART_NAME"], "System of a Down")
        self.assertEqual(songs[6]["SNG_TITLE"], "Bounce")
        self.assertEqual(songs[6]["MD5_ORIGIN"], "53bc9a023d71548cbdbdb70ec9836a29")
        self.assertEqual(songs[7]["SNG_ID"], "15523788")
        self.assertEqual(songs[7]["ART_NAME"], "System of a Down")
        self.assertEqual(songs[7]["SNG_TITLE"], "Forest")
        self.assertEqual(songs[7]["MD5_ORIGIN"], "5eeb6b94ad83f82291d5d28a1f7f6a1d")
        self.assertEqual(songs[8]["SNG_ID"], "15523790")
        self.assertEqual(songs[8]["ART_NAME"], "System of a Down")
        self.assertEqual(songs[8]["SNG_TITLE"], "ATWA")
        self.assertEqual(songs[8]["MD5_ORIGIN"], "9260b62ed22b9f8c4087a6086e2e2257")
        self.assertEqual(songs[9]["SNG_ID"], "15523791")
        self.assertEqual(songs[9]["ART_NAME"], "System of a Down")
        self.assertEqual(songs[9]["SNG_TITLE"], "Science")
        self.assertEqual(songs[9]["MD5_ORIGIN"], "3b24c6f38ceda1b1d0411685f44e35dd")
        self.assertEqual(songs[10]["SNG_ID"], "15523792")
        self.assertEqual(songs[10]["ART_NAME"], "System of a Down")
        self.assertEqual(songs[10]["SNG_TITLE"], "Shimmy")
        self.assertEqual(songs[10]["MD5_ORIGIN"], "cfb0b6287d8e289cabcf8230c7872ec0")
        self.assertEqual(songs[11]["SNG_ID"], "15523793")
        self.assertEqual(songs[11]["ART_NAME"], "System of a Down")
        self.assertEqual(songs[11]["SNG_TITLE"], "Toxicity")
        self.assertEqual(songs[11]["MD5_ORIGIN"], "2ff5bf53a6369e0b3baf069828251a10")
        self.assertEqual(songs[12]["SNG_ID"], "15523796")
        self.assertEqual(songs[12]["ART_NAME"], "System of a Down")
        self.assertEqual(songs[12]["SNG_TITLE"], "Psycho")
        self.assertEqual(songs[12]["MD5_ORIGIN"], "ece5a3e11493edc8534fbd8a38040cdf")
        self.assertEqual(songs[13]["SNG_ID"], "15523799")
        self.assertEqual(songs[13]["ART_NAME"], "System of a Down")
        self.assertEqual(songs[13]["SNG_TITLE"], "Aerials")
        self.assertEqual(songs[13]["MD5_ORIGIN"], "ded406e94f8fe78513e1e4e6e00a7151")
        self.assertEqual(songs[14]["SNG_ID"], "15523803")
        self.assertEqual(songs[14]["ART_NAME"], "System of a Down")
        self.assertEqual(songs[14]["SNG_TITLE"], "Arto")
        self.assertEqual(songs[14]["MD5_ORIGIN"], "8e43717a1585e8e080a987584d6051c9")

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
        self.assertEqual(playlist_name, "Gitarre")
        self.assertIsInstance(songs, list)
        self.assertEqual(len(songs), 13)
        for song in songs:
            song_keys = list(song.keys())
            for key in known_song_keys:
                self.assertIn(key, song_keys)
        self.assertEqual(songs[0]["SNG_ID"], "725274")
        self.assertEqual(songs[0]["ART_NAME"], "Red Hot Chili Peppers")
        self.assertEqual(songs[0]["SNG_TITLE"], "Californication")
        self.assertEqual(songs[0]["MD5_ORIGIN"], "0f951cee0984919d5453cad7e763cc04")

    def test_parse_valid_deezer_playlist_with_url(self):
        playlist_url = "https://www.deezer.com/de/playlist/3281396182"
        self._call_parse_valid_deezer_playlist(playlist_url)

    def test_parse_valid_deezer_playlist_with_id(self):
        playlist_id = "3281396182"
        self._call_parse_valid_deezer_playlist(playlist_id)

    def test_parse_invalid_deezer_playlist_with_id(self):
        invalid_playlist_id = "999999999999999999999999999"
        with self.assertRaises(DeezerApiException):
            playlist_name, songs = parse_deezer_playlist(invalid_playlist_id)

    def test_parse_invalid_input_for_deezer_playlist_with_id(self):
        invalid_playlist_id = "!\"§$%&/((;-';k(()=+ü\?"
        with self.assertRaises(DeezerApiException):
            playlist_name, songs = parse_deezer_playlist(invalid_playlist_id)

    def test_parse_invalid_deezer_playlist_with_url(self):
        invalid_playlist_url = "https://www.heise.de"
        with self.assertRaises(DeezerApiException):
            playlist_name, songs = parse_deezer_playlist(invalid_playlist_url)
    # END: parse_deezer_playlist

    
    # BEGIN: download_song
    def test_download_song_valid(self):
        song_infos = deezer_search("faber tausendfrankenlang", TYPE_TRACK)[0]
        song = get_song_infos_from_deezer_website(TYPE_TRACK, song_infos['id'])
        try:
            os.remove(test_song)
        except FileNotFoundError:
            # if we remove a file that does not exist
            pass
        download_song(song, test_song)
        file_exists = os.path.exists(test_song)
        self.assertEqual(file_exists, True)
        file_type = magic.from_file(test_song)
        self.assertEqual(file_type, "Audio file with ID3 version 2.3.0, contains:MPEG ADTS, layer III, v1, 320 kbps, 44.1 kHz, Stereo")
        os.remove(test_song)

    def test_download_song_invalid_song_type(self):
        with self.assertRaises(AssertionError):
            download_song("this sould be a dict", test_song)

    # END: download_song


class TestSpotifyMethods(unittest.TestCase):

    def _test_parse_spotify_playlist_website(self, playlist):
        songs = get_songs_from_spotify_website(playlist)
        playlist = {'Gazebo I Like Chopin', 'Ryan Paris Dolce Vita ', 'Ivana Spagna Call Me', 'Radiorama Desire', 'Baltimora Tarzan Boy', "Generazione Anni '80 Comanchero", 'Ken Laszlo Hey Hey Guy', 'P. Lion Happy Children', 'Fancy Bolero', 'Fancy Lady Of Ice', 'Miko Mission How Old Are You ', 'Scotch Disco Band', 'Sabrina Boys - Summertime Love', 'C.C. Catch Strangers by Night - Maxi-Version', 'Savage Only You', "Savage Don't Cry Tonight - Original Version", 'Italove Strangers in the Night ', "Italove L'Amour", 'Italove Follow Me to Mexico', 'Savage Celebrate - Extended Version', 'Alyne Over The Sky - Original Extended Version', "Den Harrow Don't Break My Heart", 'Savage Only You ', 'Hypnosis Pulstar', 'My Mine Hypnotic Tango - Original 12" Version', 'Fun Fun Happy Station - Scratch Version', 'Albert One Heart On Fire - Special Maxi Mix', 'Airplay For Your Love', 'M & G When I Let You Down - Extended Mix', "Bad Boys Blue You're a Woman", 'Bad Boys Blue Come Back And Stay', 'The Eight Group Life Is Life', 'The Eight Group Vamos A La Playa', 'The Eight Group The Final Countdown', "Modern Talking You're My Heart, You're My Soul '98 - New Version", 'Modern Talking Cheri Cheri Lady', 'Modern Talking Brother Louie', "Modern Talking Geronimo's Cadillac", 'Modern Talking Atlantis Is Calling ', 'Modern Talking You Are Not Alone', 'Roxette Listen to Your Heart', 'Roxette Joyride - Single Version', 'Eurythmics Sweet Dreams ', 'Eurythmics There Must Be an Angel ', 'Cyndi Lauper Girls Just Want to Have Fun', 'Cyndi Lauper Time After Time', 'Sandra In The Heat Of The Night', 'Limahl Never Ending Story', 'Samantha Fox Touch Me ', 'Fancy Slice Me Nice - Original Version', 'C.C. Catch I Can Lose My Heart Tonight - Extended Club Remix', 'C.C. Catch Heartbreak Hotel', 'The Eighty Group Moonlight Shadow', 'Erasure Always', "Modern Talking You Can Win If You Want - No 1 Mix '84", 'Modern Talking In 100 Years', 'Modern Talking Jet Airliner', 'Modern Talking Sexy Sexy Lover - Vocal Version', 'Modern Talking China in Her Eyes - Video Version', 'Modern Talking Win the Race - Radio Edit', "The Pointer Sisters I'm So Excited", 'Captain Jack Captain Jack - Short Mix', 'a-ha Take on Me', 'TOTO Africa', "Generazione Anni '80 Self Control", 'Alphaville Big in Japan - Remaster', 'Michael Sembello Maniac', 'Den Harrow Future Brain', 'Radiorama Chance To Desire ', 'F.R. David Words', 'Desireless Voyage voyage', 'Sandra Maria Magdalena - Remastered', 'Valerie Dore The Night', 'Babys Gang Happy Song', 'Radiorama Aliens', 'Babys Gang Challenger', 'Eddy Huntington Ussr', 'Silent Circle Touch in the Night - Radio Version', 'Kano Another Life - Original', 'Ken Laszlo Tonight', 'Koto Visitors', 'Max Him Lady Fantasy', 'Silent Circle Stop the Rain in the Night', 'Alphaville Sounds Like a Melody', 'Bad Boys Blue I Wanna Hear Your Heartbeat ', 'Bad Boys Blue Lady In Black', 'Bad Boys Blue A World Without You', 'Bad Boys Blue Pretty Young Girl'}
        self.assertEqual(playlist, set(songs))

    def test_spotify_parser_valid_playlist_embed_url(self):
        playlist_url = "https://open.spotify.com/embed/playlist/0wl9Q3oedquNlBAJ4MGZtS"
        self._test_parse_spotify_playlist_website(playlist_url)

    def test_spotify_parser_valid_playlist_url(self):
        playlist_url = "https://open.spotify.com/playlist/0wl9Q3oedquNlBAJ4MGZtS"
        self._test_parse_spotify_playlist_website(playlist_url)

    def test_spotify_parser_valid_playlist_id(self):
        playlist_id = "0wl9Q3oedquNlBAJ4MGZtS"
        self._test_parse_spotify_playlist_website(playlist_id)

    def test_spotify_parser_invalid_playlist_id(self):
        playlist_id = "thisdoesnotexist"
        with self.assertRaises(SpotifyWebsiteParserException):
            get_songs_from_spotify_website(playlist_id)

    def test_spotify_parser_invalid_playlist_url(self):
        playlist_url = "https://www.heise.de"
        with self.assertRaises(SpotifyWebsiteParserException):
            get_songs_from_spotify_website(playlist_url)


class TestYoutubeMethods(unittest.TestCase):

    def test_youtube_dl_valid_url(self):
        url = "https://www.youtube.com/watch?v=ZbZSe6N_BXs"
        destination_file = youtubedl_download(url, "/tmp")
        file_exists = os.path.exists(destination_file)
        self.assertEqual(file_exists, True)
        file_type = magic.from_file(destination_file)
        os.remove(destination_file)
        self.assertEqual(file_type, "Audio file with ID3 version 2.4.0, contains:MPEG ADTS, layer III, v1, 64 kbps, 48 kHz, Stereo")

    def test_youtube_dl_invalid_url(self):
        url = "https://www.heise.de"
        with self.assertRaises(YoutubeDLFailedException):
            youtubedl_download(url, "/tmp")

    def test_youtube_dl_command_execution(self):
        url = "https://www.youtube.com/watch?v=ZbZSe6N_BXs&$(touch /tmp/pwned.txt)"
        youtubedl_download(url, "/tmp")
        pwn_succeeded = os.path.exists("/tmp/pwned.txt")
        self.assertEqual(pwn_succeeded, False)


if __name__ == '__main__':
    unittest.main()
