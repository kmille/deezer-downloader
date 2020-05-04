import time
import os.path
from os.path import basename
import mpd
from zipfile import ZipFile, ZIP_DEFLATED

from configuration import config
from youtubedl import youtubedl_download, YoutubeDLFailedException, DownloadedFileNotFoundException
from spotify import get_songs_from_spotify_website, SpotifyWebsiteParserException
from deezer import TYPE_TRACK, TYPE_ALBUM, TYPE_PLAYLIST, get_song_infos_from_deezer_website, download_song, parse_deezer_playlist, deezer_search
from deezer import Deezer403Exception, Deezer404Exception, DeezerApiException

from ipdb import set_trace

from threadpool_queue import ThreadpoolScheduler, report_progress
sched = ThreadpoolScheduler()


def check_download_dirs_exist():
    for directory in [config["download_dirs"]["songs"], config["download_dirs"]["zips"], config["download_dirs"]["albums"],
                      config["download_dirs"]["playlists"], config["download_dirs"]["youtubedl"]]:
        os.makedirs(directory, exist_ok=True)


check_download_dirs_exist()


def make_song_paths_relative_to_mpd_root(songs, prefix=""):
    if not config["mpd"]["music_dir_root"].endswith("/"):
        config["mpd"]["music_dir_root"] += "/"
    songs_paths_relative_to_mpd_root = []
    for song in songs:
        songs_paths_relative_to_mpd_root.append(prefix + song[len(config["mpd"]["music_dir_root"]):])
    return songs_paths_relative_to_mpd_root


def update_mpd_db(songs, add_to_playlist):
    # songs: list of music files or just a string (file path)
    if not config["mpd"].getboolean("use_mpd"):
        return
    print("Updating mpd database")
    timeout_counter = 0
    mpd_client = mpd.MPDClient(use_unicode=True)
    try:
        mpd_client.connect(config["mpd"]["host"], config["mpd"].getint("port"))
    except ConnectionRefusedError as e:
        print("ERROR connecting to MPD ({}:{}): {}".format(config["mpd"]["host"], config["mpd"]["port"], e))
        return
    mpd_client.update()
    if add_to_playlist:
        songs = [songs] if type(songs) != list else songs
        songs = make_song_paths_relative_to_mpd_root(songs)
        while len(mpd_client.search("file", songs[0])) == 0:
            # c.update() does not block so wait for it
            if timeout_counter == 10:
                print("Tried it {} times. Give up now.".format(timeout_counter))
                return
            print("'{}' not found in the music db. Let's wait for it".format(songs[0]))
            timeout_counter += 1
            time.sleep(2)
        for song in songs:
            try:
                mpd_client.add(song)
                print("Added to mpd playlist: '{}'".format(song))
            except mpd.base.CommandError as mpd_error:
                print("ERROR adding '{}' to playlist: {}".format(song, mpd_error))


def clean_filename(path):
    return path.replace("/", "")


def get_absolute_filename(search_type, song, playlist_name=None):
    song_filename = "{} - {}.mp3".format(song['ART_NAME'], song['SNG_TITLE'])
    song_filename = clean_filename(song_filename)

    if search_type == TYPE_TRACK:
        absolute_filename = os.path.join(config["download_dirs"]["songs"], song_filename)
    elif search_type == TYPE_ALBUM:
        album_name = "{} - {}".format(song['ART_NAME'], song['ALB_TITLE'])
        album_name = clean_filename(album_name)
        album_dir = os.path.join(config["download_dirs"]["albums"], album_name)
        if not os.path.exists(album_dir):
            os.mkdir(album_dir)
        absolute_filename = os.path.join(album_dir, song_filename)
    elif search_type == TYPE_PLAYLIST:
        assert type(playlist_name) == str
        playlist_name = clean_filename(playlist_name)
        playlist_dir = os.path.join(config["download_dirs"]["playlists"], playlist_name)
        if not os.path.exists(playlist_dir):
            os.mkdir(playlist_dir)
        absolute_filename = os.path.join(playlist_dir, song_filename)

    if os.path.exists(absolute_filename):
        print("Skipping song '{}'. Already exists.".format(absolute_filename))
    else:
        print("Downloading '{}'".format(song_filename))
        download_song(song, absolute_filename)
    return absolute_filename


def create_zip_file(songs_absolute_location):
    # take first song in list and take the parent dir (name of album/playlist")
    parent_dir = songs_absolute_location[0].split("/")[-2]
    location_zip_file = os.path.join(config["download_dirs"]["zips"], "{}.zip".format(parent_dir))
    print("Creating zip file '{}'".format(location_zip_file))
    with ZipFile(location_zip_file, 'w', compression=ZIP_DEFLATED) as zip:
        for song_location in songs_absolute_location:
            try:
                print("Adding song {}".format(song_location))
                zip.write(song_location, arcname="{}/{}".format(parent_dir, basename(song_location)))
            except FileNotFoundError:
                print("Could not find file '{}'".format(song_location))
    print("Done with the zip")
    return location_zip_file


def create_m3u8_file(songs_absolute_location):
    playlist_directory, __ = os.path.split(songs_absolute_location[0])
    # 00 as prefix => will be shown as first in dir listing
    m3u8_filename = "00 {}.m3u8".format(playlist_directory.split("/")[-1])
    print("Creating m3u8 file: '{}'".format(m3u8_filename))
    m3u8_file_abs = os.path.join(playlist_directory, m3u8_filename)
    with open(m3u8_file_abs, "w") as f:
        for song in songs_absolute_location:
            if os.path.exists(song):
                f.write(basename(song) + "\n")
    # add m3u8_file so that will be zipped to
    songs_absolute_location.append(m3u8_file_abs)
    return songs_absolute_location

@sched.register_command()
def download_deezer_song_and_queue(track_id, add_to_playlist):
    song = get_song_infos_from_deezer_website(TYPE_TRACK, track_id)
    absolute_filename = get_absolute_filename(TYPE_TRACK, song)
    update_mpd_db(absolute_filename, add_to_playlist)
    return make_song_paths_relative_to_mpd_root([absolute_filename])

@sched.register_command()
def download_deezer_album_and_queue_and_zip(album_id, add_to_playlist, create_zip):
    songs = get_song_infos_from_deezer_website(TYPE_ALBUM, album_id)
    songs_absolute_location = []
    for i, song in enumerate(songs):
        report_progress(i, len(songs))
        assert type(song) == dict
        absolute_filename = get_absolute_filename(TYPE_ALBUM, song)
        songs_absolute_location.append(absolute_filename)
    update_mpd_db(songs_absolute_location, add_to_playlist)
    if create_zip:
        return [create_zip_file(songs_absolute_location)]
    return make_song_paths_relative_to_mpd_root(songs_absolute_location)

@sched.register_command()
def download_deezer_playlist_and_queue_and_zip(playlist_id, add_to_playlist, create_zip):
    playlist_name, songs = parse_deezer_playlist(playlist_id)
    songs_absolute_location = []
    for i, song in enumerate(songs):
        report_progress(i, len(songs))
        absolute_filename = get_absolute_filename(TYPE_PLAYLIST, song, playlist_name)
        songs_absolute_location.append(absolute_filename)
    update_mpd_db(songs_absolute_location, add_to_playlist)
    songs_with_m3u8_file = create_m3u8_file(songs_absolute_location)
    if create_zip:
        return [create_zip_file(songs_with_m3u8_file)]
    return make_song_paths_relative_to_mpd_root(songs_absolute_location)

@sched.register_command()
def download_spotify_playlist_and_queue_and_zip(playlist_name, playlist_id, add_to_playlist, create_zip):
    songs = get_songs_from_spotify_website(playlist_id)
    songs_absolute_location = []
    for i, song_of_playlist in enumerate(songs):
        report_progress(i, len(songs))
        # song_of_playlist: string (artist - song)
        try:
            track_id = deezer_search(song_of_playlist, TYPE_TRACK)[0]['id'] #[0] can throw IndexError
            song = get_song_infos_from_deezer_website(TYPE_TRACK, track_id)
            absolute_filename = get_absolute_filename(TYPE_PLAYLIST, song, playlist_name)
            songs_absolute_location.append(absolute_filename)
        except (IndexError, Deezer403Exception, Deezer404Exception) as msg:
            print(msg)
            return
    update_mpd_db(songs_absolute_location, add_to_playlist)
    songs_with_m3u8_file = create_m3u8_file(songs_absolute_location)
    if create_zip:
        return [create_zip_file(songs_with_m3u8_file)]
    return make_song_paths_relative_to_mpd_root(songs_absolute_location)

@sched.register_command()
def download_youtubedl_and_queue(video_url, add_to_playlist):
    filename_absolute = youtubedl_download(video_url, config["download_dirs"]["youtubedl"])
    update_mpd_db(filename_absolute, add_to_playlist)
    return make_song_paths_relative_to_mpd_root([filename_absolute])


if __name__ == '__main__':
    pass
    playlist_id = "878989033"
    #playlist_id = "1180748301"
    download_deezer_playlist_and_queue_and_zip(playlist_id, True, False)
    #moby  = "68925038"
    #download_deezer_song_and_queue(moby, False)
