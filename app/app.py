#!/usr/bin/env python3


import sys
sys.path.append("deezer")
from subprocess import Popen, PIPE
import os
import time
from functools import wraps
from threading import Thread

from flask import Flask, render_template, request, jsonify
from settings import debug_command
from deezer import deezer_search, download_deezer_song_and_queue, download_deezer_album_and_queue_and_zip, download_youtubedl_and_queue, download_spotify_playlist_and_queue_and_zip, download_deezer_playlist_and_queue_and_zip

from ipdb import set_trace
import requests

import os.path
from flask_autoindex import AutoIndex

import giphypop


app = Flask(__name__)
auto_index = AutoIndex(app, "/tmp/music/deezer", add_url_rules=False)
auto_index.add_icon_rule('music.png', ext='m3u8')

giphy = giphypop.Giphy()

# TODO: check input validation
def validate_schema(*parameters_to_check):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kw):
            j = request.get_json(force=True)
            # checks if all parameters are supplied by the user
            if set(j.keys()) != set(parameters_to_check):
                return jsonify({"error": 'Parameter not fitting. Required: {}'.format(parameters_to_check)}), 400
            if "type" in j.keys():
                if j['type'] not in ["album", "track"]:
                    return jsonify({"Error": "type muste be album or track"}),400
            if "music_id" in j.keys():
                if not isinstance(j['music_id'], int):
                    return jsonify({"Error": "music_id must be a digit"}),400
            if "add" in j.keys():
                if not isinstance(j['add'], bool):
                    return jsonify({"Error": "all must be a boolean"}),400
            if "query" in j.keys():
                if j['query'] == "":
                    return jsonify({"Error": "query is empty"}),400
            if "url" in j.keys():
                if (type(j['url']) != str) or (not j['url'].startswith("http")):
                    return jsonify({"Error": "url is not a url"}),400
            return f(*args, **kw)
        return wrapper
    return decorator


@app.route("/")
def index():
    return render_template("index.html")


@app.route('/api/v1/deezer/search', methods=['POST'])
@validate_schema("type", "query")
def search():
    """
    searches for available music in the Deezer library
    para:
        type: track|album
        query: search query
    return:
        [ { artist, music_id, (title|album) } ]
    """
    user_input = request.get_json(force=True)
    print("User request: {}".format(user_input))
    results = deezer_search(user_input['query'], user_input['type'])
    return jsonify(results)
    #return jsonify([{"artist": "Artist", "title": "title", "album": "album", "id": "12342"}])


@app.route('/api/v1/deezer/download', methods=['POST'])
@validate_schema("type", "music_id", "add_to_playlist", "create_zip")
def deezer_download():
    """
    downloads music from the Deezer library to the dir specified in settings.py
    A album will be placed in a single directory
    para:
        type: album|track
        music_id: id of the album or track
        add_to_playlist: true|false (add to mpd playlist)
    """
    user_input = request.get_json(force=True)
    print("User request: {}".format(user_input))

    if user_input['type'] == "track":
        t = Thread(target=download_deezer_song_and_queue, 
                   args=(user_input['music_id'], user_input['add_to_playlist']))
    else:
        t = Thread(target=download_deezer_album_and_queue_and_zip, 
                   args=(user_input['music_id'], user_input['add_to_playlist'], user_input['create_zip']))
    t.start()
    return jsonify({"state": "have fun"})


@app.route('/api/v1/youtubedl', methods=['POST'])
@validate_schema("url", "add_to_playlist")
def youtubedl_download():
    user_input = request.get_json(force=True)
    print("User request: {}".format(user_input))
    t = Thread(target=download_youtubedl_and_queue,
               args=(user_input['url'], user_input['add_to_playlist']))
    t.start()
    return jsonify({"state": "have fun youtubedl"})


@app.route('/api/v1/spotify', methods=['POST'])
@validate_schema("playlist_name", "playlist_url", "add_to_playlist", "create_zip")
def spotify_playlist_download():
    user_input = request.get_json(force=True)
    print("User request: {}".format(user_input))

    t = Thread(target=download_spotify_playlist_and_queue_and_zip,
               args=(user_input['playlist_name'],
                     user_input['playlist_url'],
                     user_input['add_to_playlist'],
                     user_input['create_zip']))
    t.start()
    return jsonify({"state": "have fun spotify"})


@app.route('/api/v1/deezer/playlist', methods=['POST'])
@validate_schema("playlist_url", "add_to_playlist", "create_zip")
def deezer_playlist_download():
    user_input = request.get_json(force=True)
    print("User request: {}".format(user_input))
    t = Thread(target=download_deezer_playlist_and_queue_and_zip,
               args=(user_input['playlist_url'],
                     user_input['add_to_playlist'],
                     user_input['create_zip']))
    t.start()
    return jsonify({"state": "have fun deezer"})


@app.route("/debug")
def debug():
    p = Popen(debug_command, shell=True, stdout=PIPE)
    p.wait()
    stdout, __ = p.communicate()
    return jsonify({'debug_msg': stdout.decode()})


@app.route("/downloads/")
@app.route("/downloads/<path:path>")
def autoindex(path="."):
    try:
        gif = giphy.random_gif(tag="cat")
        media_url = gif.media_url
    except requests.exceptions.HTTPError:
        # theh api is limited
        media_url = "https://cataas.com/cat"

    template_context = {'gif_url': media_url}
    print(template_context)
    return auto_index.render_autoindex(path, template_context=template_context)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
