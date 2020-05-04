#!/usr/bin/env python3
from subprocess import Popen, PIPE
from functools import wraps
from threading import Thread
import requests
import atexit
from flask import Flask, render_template, request, jsonify
from flask_autoindex import AutoIndex
import giphypop

from music_backend import sched
from deezer import deezer_search, start_deezer_keepalive, stop_deezer_keepalive, is_deezer_session_valid
from configuration import config

from ipdb import set_trace


app = Flask(__name__)
auto_index = AutoIndex(app, config["download_dirs"]["base"], add_url_rules=False)
auto_index.add_icon_rule('music.png', ext='m3u8')

giphy = giphypop.Giphy()


@app.route("/")
def index():
    return render_template("index.html",
            api_root=config["http"]["api_root"], static_root=config["http"]["static_root"], 
            deezer_is_working=is_deezer_session_valid())


@app.route("/debug")
def show_debug():
    p = Popen(config["debug"]["command"], shell=True, stdout=PIPE)
    p.wait()
    stdout, __ = p.communicate()
    return jsonify({'debug_msg': stdout.decode()})


@app.route("/downloads/")
@app.route("/downloads/<path:path>")
def autoindex(path="."):
    # directory index - flask version (let the user download mp3/zip in the browser)
    try:
        gif = giphy.random_gif(tag="cat")
        media_url = gif.media_url
    except requests.exceptions.HTTPError:
        # the api is rate-limited. Fallback:
        media_url = "https://cataas.com/cat"

    template_context = {'gif_url': media_url}
    return auto_index.render_autoindex(path, template_context=template_context)


def validate_schema(*parameters_to_check):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kw):
            j = request.get_json(force=True)
            print("User request: {} with {}".format(request.path, j))
            # checks if all parameters are supplied by the user
            if set(j.keys()) != set(parameters_to_check):
                return jsonify({"error": 'parameters not fitting. Required: {}'.format(parameters_to_check)}), 400
            if "type" in j.keys():
                if j['type'] not in ["album", "track", "album_track"]:
                    return jsonify({"error": "type must be album, track or album_track"}), 400
            if "music_id" in j.keys():
                if type(j['music_id']) != int:
                    return jsonify({"error": "music_id must be a integer"}), 400
            if "add_to_playlist" in j.keys():
                if type(j['add_to_playlist']) != bool:
                    return jsonify({"error": "add_to_playlist must be a boolean"}), 400
            if "create_zip" in j.keys():
                if type(j['create_zip']) != bool:
                    return jsonify({"error": "create_zip must be a boolean"}), 400
            if "query" in j.keys():
                if type(j['query']) != str:
                    return jsonify({"error": "query is not a string"}), 400
                if j['query'] == "":
                    return jsonify({"error": "query is empty"}), 400
            if "url" in j.keys():
                if (type(j['url']) != str) or (not j['url'].startswith("http")):
                    return jsonify({"error": "url is not a url. http... only"}), 400
            if "playlist_url" in j.keys():
                if type(j['playlist_url']) != str:
                    return jsonify({"error": "playlist_url is not a string"}), 400
                if len(j['playlist_url'].strip()) == 0:
                    return jsonify({"error": "playlist_url is empty"}), 400
            if "playlist_name" in j.keys():
                if type(j['playlist_name']) != str:
                    return jsonify({"error": "playlist_name is not a string"}), 400
                if len(j['playlist_name'].strip()) == 0:
                    return jsonify({"error": "playlist_name is empty"}), 400
            return f(*args, **kw)
        return wrapper
    return decorator


@app.route('/queue', methods=['GET'])
def show_queue():
    """
    shows queued tasks
    return:
        json: [ { description, command } ]
    """
    results = [
        { 'id': id(task), 'description': task.description, 'command': task.fn_name, 'args': task.kwargs, 'state': task.state,
         'result': task.result, 'exception': str(task.exception),
          'progress': [task.progress, task.progress_maximum] }
        for task in sched.all_tasks
    ]
    return jsonify(results)

@app.route('/search', methods=['POST'])
@validate_schema("type", "query")
def search():
    """
    searches for available music in the Deezer library
    para:
        type: track|album|album_track
        query: search query
    return:
        json: [ { artist, id, (title|album) } ]
    """
    user_input = request.get_json(force=True)
    results = deezer_search(user_input['query'], user_input['type'])
    return jsonify(results)


@app.route('/download', methods=['POST'])
@validate_schema("type", "music_id", "add_to_playlist", "create_zip")
def deezer_download_song_or_album():
    """
    downloads a song or an album from Deezer to the dir specified in settings.py
    para:
        type: album|track
        music_id: id of the album or track (int)
        add_to_playlist: True|False (add to mpd playlist)
        create_zip: True|False (create a zip for the album)
    """
    user_input = request.get_json(force=True)
    desc = "I'm working on the {}".format(user_input['type'])
    if user_input['type'] == "track":
        task = sched.enqueue_task(desc, "download_deezer_song_and_queue",
                    track_id=user_input['music_id'], add_to_playlist=user_input['add_to_playlist'])
    else:
        task = sched.enqueue_task(desc, "download_deezer_album_and_queue_and_zip",
                   album_id=user_input['music_id'], add_to_playlist=user_input['add_to_playlist'], create_zip=user_input['create_zip'])
    return jsonify({"task_id": id(task), })


@app.route('/youtubedl', methods=['POST'])
@validate_schema("url", "add_to_playlist")
def youtubedl_download():
    """
    takes an url and tries to download it via youtuble-dl
    para:
        url: link to youtube (or something youtube-dl supports)
        add_to_playlist: True|False (add to mpd playlist)
    """
    user_input = request.get_json(force=True)
    desc = "I ❤ ABBA"
    task = sched.enqueue_task(desc, "download_youtubedl_and_queue",
               video_url=user_input['url'], add_to_playlist=user_input['add_to_playlist'])
    return jsonify({"task_id": id(task), })


@app.route('/playlist/deezer', methods=['POST'])
@validate_schema("playlist_url", "add_to_playlist", "create_zip")
def deezer_playlist_download():
    """
    downloads songs of a public Deezer playlist.
    A directory with the name of the playlist will be created.
    para:
        playlist_url: link to a public Deezer playlist (the id of the playlist works too)
        add_to_playlist: True|False (add to mpd playlist)
        create_zip: True|False (create a zip for the playlist)
    """
    user_input = request.get_json(force=True)
    desc = "I'm working on your Deezer playlist"
    task = sched.enqueue_task(desc, "download_deezer_playlist_and_queue_and_zip",
                playlist_id=user_input['playlist_url'],
                add_to_playlist=user_input['add_to_playlist'],
                create_zip=user_input['create_zip'])
    return jsonify({"task_id": id(task), })


@app.route('/playlist/spotify', methods=['POST'])
@validate_schema("playlist_name", "playlist_url", "add_to_playlist", "create_zip")
def spotify_playlist_download():
    """
      1. /GET and parse the Spotify playlist (html)
      2. search every single song on Deezer. Use the first hit
      3. download the song from Deezer
    para:
        playlist_name: name of the playlist (used for the subfolder)
        playlist_url: link to Spotify playlist or just the id of it
        add_to_playlist: True|False (add to mpd playlist)
        create_zip: True|False (create a zip for the playlist)
    """
    user_input = request.get_json(force=True)
    desc = "I'm working on your Spotify playlist"
    task = sched.enqueue_task(desc, "download_spotify_playlist_and_queue_and_zip",
                     playlist_name=user_input['playlist_name'],
                     playlist_id=user_input['playlist_url'],
                     add_to_playlist=user_input['add_to_playlist'],
                     create_zip=user_input['create_zip'])
    return jsonify({"task_id": id(task), })


if config.getint('deezer', 'keepalive', fallback=0) > 0:
    start_deezer_keepalive()

sched.run_workers(config.getint('threadpool', 'workers'))

@atexit.register
def stop_workers():
    sched.stop_workers()
    stop_deezer_keepalive()

if __name__ == '__main__':
    app.run(port=5000, debug=True, use_reloader=False)

