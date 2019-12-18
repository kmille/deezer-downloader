from os.path import join
from credentials import sid

use_mpd = True
mpd_host = "localhost"
mpd_port = 6600

mpd_music_dir_root = "/var/lib/mpd/music"
download_dir_base = "/var/lib/mpd/music/downloads"

download_dir_songs = join(download_dir_base, "songs")
download_dir_albums = join(download_dir_base, "albums")
download_dir_zips = join(download_dir_base, "zips")
download_dir_playlists = join(download_dir_base, "playlists")
download_dir_youtubedl = join(download_dir_base, "youtube-dl")

debug_command = "journalctl -u deezer-downloader -n 100 --output cat"
