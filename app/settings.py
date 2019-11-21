from credentials import sid

use_mpd = True
mpd_host = "localhost"
mpd_port = 6600

behind_reverse_proxy = False
reverse_proxy_path = "/foo"


mpd_music_dir_root = "/tmp/music"
# TODO: docs: for songs and albums
deezer_download_dir_songs = "/tmp/music/deezer/songs"
deezer_download_dir_albums = "/tmp/music/deezer/albums"
download_dir_zips = "/tmp/music/deezer/zips"
spotify_download_dir_playlists = "/tmp/music/deezer/spotify-playlists"
youtubedl_download_dir = "/tmp/music/deezer/youtube-dl"

deezer_download_dir_playlists = "/tmp/music/deezer/deezer-playlists"

debug_command = "journalctl -u wpa_supplicant@wlp3s0.service --output=cat -n 50"
#debug_command = "head -n 50 deezer.log"
