#!/usr/bin/env python3
import os
from pathlib import Path
from subprocess import Popen, PIPE
from functools import wraps
import atexit
from flask import Flask, render_template, request, jsonify, send_from_directory, abort
from markupsafe import escape
import warnings
import giphypop

from deezer_downloader.configuration import config
from deezer_downloader.web.music_backend import sched
from deezer_downloader.deezer import deezer_search, init_deezer_session

app = Flask(__name__)

warnings.filterwarnings("ignore", message="You are using the giphy public api key")
giphy = giphypop.Giphy()
BASE_DIR = Path(config["download_dirs"]["base"]).resolve()


def init():
    sched.run_workers(config.getint('threadpool', 'workers'))
    init_deezer_session(config['proxy']['server'],
                        config['deezer']['quality'])

    @atexit.register
    def stop_workers():
        sched.stop_workers()


init()


# user input validation
def validate_schema(*parameters_to_check):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kw):
            j = request.get_json(force=True)
            print("User request: {} with {}".format(request.path, j))
            # check if all parameters are supplied by the user
            if set(j.keys()) != set(parameters_to_check):
                return jsonify({"error": 'parameters missing, required fields: {}'.format(parameters_to_check)}), 400
            if "type" in j.keys():
                if j['type'] not in ["album", "track", "artist", "album_track", "artist_album", "artist_top"]:
                    return jsonify({"error": "type must be album, track, artist, album_track, artist_album or artist_top"}), 400
            if "music_id" in j.keys():
                if type(j['music_id']) is not int:
                    return jsonify({"error": "music_id must be a integer"}), 400
            if "add_to_playlist" in j.keys():
                if type(j['add_to_playlist']) is not bool:
                    return jsonify({"error": "add_to_playlist must be a boolean"}), 400
            if "create_zip" in j.keys():
                if type(j['create_zip']) is not bool:
                    return jsonify({"error": "create_zip must be a boolean"}), 400
            if "query" in j.keys():
                if type(j['query']) is not str:
                    return jsonify({"error": "query is not a string"}), 400
                if j['query'] == "":
                    return jsonify({"error": "query is empty"}), 400
            if "url" in j.keys():
                if (type(j['url']) is not str) or (not j['url'].startswith("http")):
                    return jsonify({"error": "url is not a url. http... only"}), 400
            if "playlist_url" in j.keys():
                if type(j['playlist_url']) is not str:
                    return jsonify({"error": "playlist_url is not a string"}), 400
                if len(j['playlist_url'].strip()) == 0:
                    return jsonify({"error": "playlist_url is empty"}), 400
            if "playlist_name" in j.keys():
                if type(j['playlist_name']) is not str:
                    return jsonify({"error": "playlist_name is not a string"}), 400
                if len(j['playlist_name'].strip()) == 0:
                    return jsonify({"error": "playlist_name is empty"}), 400
            if "user_id" in j.keys():
                if type(j['user_id']) is not str or not j['user_id'].isnumeric():
                    return jsonify({"error": "user_id must be a numeric string"}), 400
            return f(*args, **kw)
        return wrapper
    return decorator


@app.route("/")
def index():
    return render_template("index.html",
                           api_root=config["http"]["api_root"],
                           static_root=config["http"]["static_root"],
                           use_mpd=str(config['mpd'].getboolean('use_mpd')).lower())


@app.route("/debug")
def show_debug():
    if "LOG_FILE" in os.environ:
        # check env LOG_FILE in Dockerfile
        # overwriting config value when using Docker
        cmd = f"tail -n 100 {os.environ['LOG_FILE']}"
    else:
        cmd = config["debug"]["command"]
    p = Popen(cmd, shell=True, stdout=PIPE)
    p.wait()
    stdout, __ = p.communicate()
    return jsonify({'debug_msg': stdout.decode()})


@app.route("/downloads/")
@app.route("/downloads/<path:path>")
def autoindex(path="."):
    requested = (BASE_DIR / path).resolve()

    if BASE_DIR not in requested.parents and requested != BASE_DIR:
        abort(403)
    if not requested.exists():
        abort(404)

    if requested.is_file():
        as_attachment = request.args.get("as_attachment", "true").lower() == "true"
        return send_from_directory(requested.parent, requested.name, as_attachment=as_attachment)

    rel_path = requested.relative_to(BASE_DIR)
    entries = []

    # check if BASE_DIR - requested path = same path
    if rel_path != Path("."):
        parent = "" if rel_path.parent == Path(".") else str(rel_path.parent)
        entries.append({"name": "..", "path": parent, "is_dir": True})

    for entry in sorted(requested.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        entry_rel = entry.name if rel_path == Path(".") else str(rel_path / entry.name)
        entries.append({
            "name": entry.name,
            "path": entry_rel,
            "is_dir": entry.is_dir(),
            "size": f"{round(entry.stat().st_size / (1000 ** 2), 2)} MB"
        })

    return render_template(
        "autoindex.html",
        entries=entries,
        current_path="" if rel_path == Path(".") else str(rel_path),
    )


@app.route('/queue', methods=['GET'])
def show_queue():
    """
    shows queued tasks
    return:
        json: [ { tasks } ]
    """
    results = [
        {'id': id(task),
         'description': escape(task.description),
         #'command': task.fn_name,
         'args': escape(task.kwargs),
         'state': escape(task.state),
         'result': escape(task.result),
         'exception': escape(str(task.exception)),
         'progress': [task.progress, task.progress_maximum]
        } for task in sched.all_tasks
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
    desc = "Downloading {}".format(user_input['type'])
    if user_input['type'] == "track":
        task = sched.enqueue_task(desc, "download_deezer_song_and_queue",
                                  track_id=user_input['music_id'],
                                  add_to_playlist=user_input['add_to_playlist'])
    else:
        task = sched.enqueue_task(desc, "download_deezer_album_and_queue_and_zip",
                                  album_id=user_input['music_id'],
                                  add_to_playlist=user_input['add_to_playlist'],
                                  create_zip=user_input['create_zip'])
    return jsonify({"task_id": id(task), })


@app.route('/import/csv', methods=['POST'])
def csv_import_download():
    """Queue tracks or albums described by rows imported from a CSV file."""
    user_input = request.get_json(silent=True)
    if not isinstance(user_input, dict):
        return jsonify({"error": "request body must be JSON"}), 400

    required = {"type", "rows", "add_to_playlist", "create_zip"}
    if set(user_input) != required:
        return jsonify({"error": "required fields: type, rows, add_to_playlist, create_zip"}), 400
    if user_input["type"] not in ("track", "album"):
        return jsonify({"error": "type must be track or album"}), 400
    if not isinstance(user_input["add_to_playlist"], bool) or not isinstance(user_input["create_zip"], bool):
        return jsonify({"error": "add_to_playlist and create_zip must be booleans"}), 400
    rows = user_input["rows"]
    if not isinstance(rows, list) or not rows or len(rows) > 10000:
        return jsonify({"error": "rows must contain between 1 and 10000 entries"}), 400
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"artist", "title", "album"}:
            return jsonify({"error": "each row must contain artist, title and album"}), 400
        if any(not isinstance(value, str) for value in row.values()):
            return jsonify({"error": "row values must be strings"}), 400
        needed = "title" if user_input["type"] == "track" else "album"
        if not row[needed].strip():
            return jsonify({"error": f"every row must have a {needed}"}), 400

    task = sched.enqueue_task(
        f"Downloading CSV {user_input['type']} import ({len(rows)} rows)",
        "download_csv_import",
        rows=rows,
        download_type=user_input["type"],
        add_to_playlist=user_input["add_to_playlist"],
        create_zip=user_input["create_zip"],
    )
    return jsonify({"task_id": id(task), "row_count": len(rows)})


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
    desc = "Downloading via youtube-dl"
    task = sched.enqueue_task(desc, "download_youtubedl_and_queue",
                              video_url=user_input['url'],
                              add_to_playlist=user_input['add_to_playlist'])
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
    desc = "Downloading Deezer playlist"
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
    desc = "Downloading Spotify playlist"
    task = sched.enqueue_task(desc, "download_spotify_playlist_and_queue_and_zip",
                              playlist_name=user_input['playlist_name'],
                              playlist_id=user_input['playlist_url'],
                              add_to_playlist=user_input['add_to_playlist'],
                              create_zip=user_input['create_zip'])
    return jsonify({"task_id": id(task), })


@app.route('/favorites/deezer', methods=['POST'])
@validate_schema("user_id", "add_to_playlist", "create_zip")
def deezer_favorites_download():
    """
    downloads favorite songs of a Deezer user (looks like this in the brwoser:
       https://www.deezer.com/us/profile/%%user_id%%/loved)
    a subdirecotry with the name of the user_id will be created.
    para:
        user_id: deezer user_id
        add_to_playlist: True|False (add to mpd playlist)
        create_zip: True|False (create a zip for the playlist)
    """
    user_input = request.get_json(force=True)
    desc = "Downloading Deezer favorites"
    task = sched.enqueue_task(desc, "download_deezer_favorites",
                              user_id=user_input['user_id'],
                              add_to_playlist=user_input['add_to_playlist'],
                              create_zip=user_input['create_zip'])
    return jsonify({"task_id": id(task), })
