#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys
sys.path.append("deezer")
import os
import time
from functools import wraps
from threading import Thread

from flask import Flask, render_template, request, jsonify
from settings import update_mpd
from deezer import deezerSearch, my_list_album, my_download_song, my_download_album 
from youtube import youtubedl_download

from ipdb import set_trace

app = Flask(__name__)

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
                    return jsonify({"Error": "add must be a boolean"}),400
            if "query" in j.keys():
                if j['query'] == "":
                    return jsonify({"Error": "query is empty"}),400
            if "url" in j.keys():
                if (type(j['url']) != unicode) or (not j['url'].startswith("http")):
                    return jsonify({"Error": "url is not a url"}),400
            return f(*args, **kw)
        return wrapper
    return decorator


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
    query, type = request.get_json(force=True).values()
    results = deezerSearch(query, type)
    return jsonify(results)


@app.route('/api/v1/deezer/album/list', methods=['POST'])
@validate_schema("music_id")
def list_album():
    """
    para:
        music_id (int): id of the album
    return:
        [ { album,artist,song_id,title}]
    """
    music_id = request.get_json(force=True)['music_id']
    return jsonify(my_list_album(music_id))


@app.route('/api/v1/deezer/download', methods=['POST'])
@validate_schema("type", "music_id", "add")
def download():
    """
    downloads music from the Deezer library to the dir specified in settings.py
    A album will be placed in a single directory
    para: 
        type: album|track
        music_id: id of the album or track
        add: true|false (add to mpd playlist)
    """
    add, music_id, type = request.get_json(force=True).values()
    target = my_download_song if type == "track" else my_download_album
    t = Thread(target=target, args=(music_id, update_mpd, add))
    t.start()
    return jsonify({"state": "have fun"})


@app.route('/api/v1/youtube-dl/download', methods=['POST'])
@validate_schema("url", "add")
def download_youtubedl():
    """
    downloads music from with youtube-dl
    para:
        url: url that goes into youtube-dl
        add: true|false (add to mpd playlist)
    """
    url, add = request.get_json(force=True).values()
    t = Thread(target=youtubedl_download, args=(url, add))
    t.start()
    return jsonify({"state": "have fun"})


@app.route('/static/<path:filename>')
def serve_static(filename):
    root_dir = os.path.dirname(os.getcwd())
    return send_from_directory(os.path.join(root_dir, 'static'), filename)    


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/youtube-dl")
def show_youtube():
    return render_template("youtube.html")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
