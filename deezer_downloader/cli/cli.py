#!/usr/bin/env python3

# File: cli.py
# Author: Hadi Cahyadi <cumulus13@gmail.com>
# Date: 2026-05-10
# Description: 
# License: MIT

"""
deezer-cli — Interactive colorful CLI client for deezer-downloader
Connects to a running deezer-downloader server (default: http://localhost:5000)

Real API (from app.py + custom.js):
  POST /search          {type, query}
  POST /download        {type, music_id, add_to_playlist, create_zip}
  POST /youtubedl       {url, add_to_playlist}
  POST /playlist/deezer {playlist_url, add_to_playlist, create_zip}
  POST /playlist/spotify{playlist_name, playlist_url, add_to_playlist, create_zip}
  POST /favorites/deezer{user_id, add_to_playlist, create_zip}
  GET  /queue
  GET  /debug

Search types: track | album | artist | album_track | artist_album | artist_top
Download types: track | album

Usage:
  python deezer_cli.py                  # interactive mode
  python deezer_cli.py --host http://host:5001
  python deezer_cli.py search "Adele"
  python deezer_cli.py dl track 8086130
"""

import argparse
import json
import os
import sys
import textwrap
from typing import Optional

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")

# ── ANSI colour helpers ───────────────────────────────────────────────────────

RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
RED     = "\033[31m"
GREEN   = "\033[32m"
YELLOW  = "\033[33m"
MAGENTA = "\033[35m"
CYAN    = "\033[36m"
WHITE   = "\033[37m"

def c(text, *codes):
    return "".join(codes) + str(text) + RESET

def ok(msg):   print(c(f"  \u2705  {msg}", GREEN, BOLD))
def err(msg):  print(c(f"  \u274c  {msg}", RED, BOLD))
def warn(msg): print(c(f"  \u26a0\ufe0f   {msg}", YELLOW))
def info(msg): print(c(f"  \u2139\ufe0f   {msg}", CYAN))
def sep():     print(c("\u2500" * 62, DIM))

# ── API client ────────────────────────────────────────────────────────────────

class DeezerClient:
    def __init__(self, base: str = "http://localhost:5000"):
        self.base = base.rstrip("/")
        self.session = requests.Session()

    def _post(self, path, payload: dict):
        url = f"{self.base}{path}"
        try:
            r = self.session.post(
                url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=20,
            )
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"Cannot reach server at {self.base}")
        except requests.exceptions.HTTPError:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")

    def _get(self, path):
        url = f"{self.base}{path}"
        try:
            r = self.session.get(url, timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"Cannot reach server at {self.base}")
        except requests.exceptions.HTTPError:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")

    def ping(self) -> bool:
        try:
            r = self.session.get(f"{self.base}/", timeout=5)
            return r.status_code < 500
        except Exception:
            return False

    def search(self, query: str, search_type: str = "track"):
        return self._post("/search", {"type": search_type, "query": str(query)})

    def download(self, music_id: int, dl_type: str,
                 add_to_playlist: bool = False, create_zip: bool = False):
        return self._post("/download", {
            "type": dl_type,
            "music_id": int(music_id),
            "add_to_playlist": add_to_playlist,
            "create_zip": create_zip,
        })

    def download_youtube(self, url: str, add_to_playlist: bool = False):
        return self._post("/youtubedl", {"url": url, "add_to_playlist": add_to_playlist})

    def download_deezer_playlist(self, playlist_url: str,
                                 add_to_playlist: bool = False, create_zip: bool = False):
        return self._post("/playlist/deezer", {
            "playlist_url": str(playlist_url),
            "add_to_playlist": add_to_playlist,
            "create_zip": create_zip,
        })

    def download_spotify_playlist(self, playlist_name: str, playlist_url: str,
                                  add_to_playlist: bool = False, create_zip: bool = False):
        return self._post("/playlist/spotify", {
            "playlist_name": playlist_name,
            "playlist_url": playlist_url,
            "add_to_playlist": add_to_playlist,
            "create_zip": create_zip,
        })

    def download_favorites(self, user_id: str,
                           add_to_playlist: bool = False, create_zip: bool = False):
        return self._post("/favorites/deezer", {
            "user_id": str(user_id),
            "add_to_playlist": add_to_playlist,
            "create_zip": create_zip,
        })

    def queue(self):
        return self._get("/queue")

    def debug(self):
        return self._get("/debug")


# ── result printers ───────────────────────────────────────────────────────────

def print_tracks(results: list):
    if not results:
        warn("No results found.")
        return
    sep()
    print(c(f"  \U0001f3b5  {len(results)} track(s)", BOLD))
    sep()
    for i, r in enumerate(results, 1):
        idx    = c(f"[{i:>2}]", DIM)
        artist = c(r.get("artist", "?"), MAGENTA)
        title  = c(r.get("title", "?"), WHITE, BOLD)
        album  = c(r.get("album", ""), DIM)
        tid    = c(f"id={r.get('id', '?')}", DIM)
        print(f"  {idx}  {artist} \u2014 {title}  {album}  {tid}")
    sep()
    info(f"Use  {c('dl track <id or #N>', YELLOW)}  to download")


def print_albums(results: list):
    if not results:
        warn("No results found.")
        return
    sep()
    print(c(f"  \U0001f4bf  {len(results)} album(s)", BOLD))
    sep()
    # for i, r in enumerate(results, 1):
    sorted_results = sorted(
        results,
        key=lambda x: int(x.get("album_id") or x.get("id") or 0),
        reverse=True,
    )

    for i, r in enumerate(sorted_results, 1):
        idx    = c(f"[{i:>2}]", DIM)
        artist = c(r.get("artist", "?"), MAGENTA)
        album  = c(r.get("album", "?"), WHITE, BOLD)
        aid    = c(f"id={r.get('id','?')}  album_id={r.get('album_id','?')}", DIM)
        print(f"  {idx}  {artist} \u2014 {album}  {aid}")
    sep()
    info(f"Use  {c('dl album <album_id or #N>', YELLOW)}  to download")
    info(f"Use  {c('list #N', YELLOW)}  to list tracks inside an album")


def print_artists(results: list):
    if not results:
        warn("No results found.")
        return
    sep()
    print(c(f"  \U0001f3a4  {len(results)} artist(s)", BOLD))
    sep()
    for i, r in enumerate(results, 1):
        idx    = c(f"[{i:>2}]", DIM)
        artist = c(r.get("artist", "?"), WHITE, BOLD)
        aid    = c(f"artist_id={r.get('artist_id','?')}", DIM)
        print(f"  {idx}  {artist}  {aid}")
    sep()
    info(f"Use  {c('albums-of <artist_id or #N>', YELLOW)}  or  {c('top <artist_id or #N>', YELLOW)}")


def _show_resp(resp):
    if not resp:
        warn("Empty response from server.")
        return
    task_id = resp.get("task_id") if isinstance(resp, dict) else None
    if task_id:
        ok(f"Queued successfully! task_id={task_id}")
    else:
        ok(f"Response: {json.dumps(resp)[:200]}")


# ── interactive REPL ──────────────────────────────────────────────────────────

HELP_TEXT = f"""
{c("Available commands", BOLD, CYAN)}

  {c("Search", YELLOW, BOLD)}
    {c("search", YELLOW)} <query>            search tracks  (alias: s)
    {c("albums", YELLOW)} <query>            search albums
    {c("artists", YELLOW)} <query>           search artists
    {c("artist", YELLOW)} <query>            search artists
    {c("ar", YELLOW)} <query>                search artists
    {c("list", YELLOW)} <album_id|#N>        list tracks in an album
    {c("l", YELLOW)} <album_id|#N>           list tracks in an album
    {c("albums-of", YELLOW)} <artist_id|#N>  list albums by artist
    {c("al", YELLOW)} <artist_id|#N>  list albums by artist
    {c("top", YELLOW)} <artist_id|#N>        top tracks by artist

  {c("Download", YELLOW, BOLD)}
    {c("dl track", YELLOW)} <id|#N>          download a track  (alias: dl t)
    {c("dl album", YELLOW)} <album_id|#N>    download an album  (alias: dl a)
    {c("dl zip", YELLOW)} <album_id|#N>      download album as zip file
    {c("dl playlist", YELLOW)} <url_or_id>   download Deezer playlist
    {c("dl spotify", YELLOW)} <name> <url>   download Spotify playlist
    {c("dl youtube", YELLOW)} <url>          download via yt-dlp  (alias: dl yt)
    {c("dl favorites", YELLOW)} <user_id>    download Deezer favorites

  {c("Other", YELLOW, BOLD)}
    {c("queue", YELLOW)}                     show download queue / progress
    {c("qu", YELLOW)}                        show download queue / progress
    {c("debug", YELLOW)}                     show server debug log
    {c("help", YELLOW)}                      show this help
    {c("quit/q", YELLOW)} / {c("exit", YELLOW)}            exit

  {c("Tip:", DIM)} After a search, use {c('#N', YELLOW)} (e.g. {c('dl track #3', YELLOW)}) to reference results by number.
"""


class REPL:
    def __init__(self, client: DeezerClient):
        self.client = client
        self._last_tracks: list = []
        self._last_albums: list = []
        self._last_artists: list = []

    def run(self):
        print(f"\n  {c(chr(0x1f3b6)+'  deezer-cli', CYAN, BOLD)}  {c('interactive mode', DIM)}")
        print(f"  Server \u2192 {c(self.client.base, CYAN, BOLD)}")
        print(f"  Type {c('help', YELLOW)} for commands, {c('quit', RED)} to exit\n")

        if not self.client.ping():
            err(f"Server not reachable at {self.client.base}")
            err("Start it with:  deezer-downloader --config config.ini")
            sys.exit(1)
        ok("Connected to server")

        while True:
            try:
                raw = input(f"\n{c('deezer', MAGENTA, BOLD)}{c('>', DIM)} ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not raw:
                continue

            parts = raw.split()
            cmd = parts[0].lower()


            known_commands = {
                "search", "s",
                "albums",
                "al",
                "ar",
                "artists",
                "artist",
                "list",
                "l",
                "albums-of",
                "top",
                "dl",
                "queue",
                "qu",
                "debug",
                "help",
                "quit",
                "exit",
                "q",
            }

            try:
                if cmd and cmd in known_commands:
                    if cmd in ("quit", "exit", "q"):
                        break
                    elif cmd == "help":
                        print(HELP_TEXT)
                    elif cmd in ("search", "s"):
                        self._cmd_search(parts, "track")
                    elif cmd == "albums":
                        self._cmd_search(parts, "album")
                    elif cmd in ("artists", "artist", "ar"):
                        self._cmd_search(parts, "artist")
                    elif cmd in ("list", "l"):
                        self._cmd_list(parts)
                    elif cmd in ("albums-of", "al"):
                        self._cmd_artist_browse(parts, "artist_album")
                    elif cmd == "top":
                        self._cmd_artist_browse(parts, "artist_top")
                    elif cmd == "dl":
                        self._cmd_dl(parts)
                    elif cmd in ("queue", "qu"):
                        self._cmd_queue()
                    elif cmd == "debug":
                        self._cmd_debug()
                    else:
                        warn(f"Unknown command '{cmd}'. Type {c('help', YELLOW)} for help.")
                        
                else:
                    if cmd:
                        warn(f"Unknown command '{cmd}'. Type {c('help', YELLOW)} for help.")
                        # fallback → treat unknown input as artist search
                        query = raw.strip()

                        info(f"Searching artists for {c(repr(query), WHITE)}...")

                        results = self.client.search(query, "artist")

                        self._last_artists = results
                        print_artists(results)
                    else:
                        warn(f"Type {c('help', YELLOW)} for help.")
                    
            except RuntimeError as e:
                err(str(e))
            except Exception as e:
                err(f"Unexpected error: {type(e).__name__}: {e}")

        print(c(f"\n  {chr(0x1f44b)}  Bye!\n", CYAN, BOLD))

    # ── command handlers ──────────────────────────────────────────────────────

    def _cmd_search(self, parts, stype):
        if len(parts) < 2:
            warn(f"Usage: {parts[0]} <query>")
            return
        query = " ".join(parts[1:])
        info(f"Searching {stype}s for {c(repr(query), WHITE)}...")
        results = self.client.search(query, stype)
        if stype == "track":
            self._last_tracks = results
            print_tracks(results)
        elif stype == "album":
            self._last_albums = results
            print_albums(results)
        elif stype == "artist":
            self._last_artists = results
            print_artists(results)

    def _cmd_list(self, parts):
        if len(parts) < 2:
            warn("Usage: list <album_id|#N>")
            return
        aid = self._resolve_album_id(parts[1])
        if aid is None:
            return
        info(f"Listing tracks in album {c(aid, CYAN)}...")
        results = self.client.search(str(aid), "album_track")
        self._last_tracks = results
        print_tracks(results)

    def _cmd_artist_browse(self, parts, stype):
        if len(parts) < 2:
            warn(f"Usage: {parts[0]} <artist_id|#N>")
            return
        aid = self._resolve_artist_id(parts[1])
        if aid is None:
            return
        info(f"Fetching {stype} for artist {c(aid, CYAN)}...")
        results = self.client.search(str(aid), stype)
        if stype == "artist_top":
            self._last_tracks = results
            print_tracks(results)
        else:
            self._last_albums = results
            print_albums(results)

    def _cmd_dl(self, parts):
        if len(parts) < 2:
            warn("Usage: dl <track|album|zip|playlist|spotify|youtube|favorites> ...")
            return
        sub = parts[1].lower()

        if sub in ("track", "t"):
            if len(parts) < 3:
                warn("Usage: dl track <id|#N>")
                return
            tid = self._resolve_track_id(parts[2])
            if tid is None: return
            info(f"Queuing track {c(tid, CYAN)}...")
            _show_resp(self.client.download(tid, "track"))

        elif sub in ("album", "a"):
            if len(parts) < 3:
                warn("Usage: dl album <album_id|#N>")
                return
            aid = self._resolve_album_id(parts[2])
            if aid is None: return
            info(f"Queuing album {c(aid, CYAN)}...")
            _show_resp(self.client.download(aid, "album"))

        elif sub == "zip":
            if len(parts) < 3:
                warn("Usage: dl zip <album_id|#N>")
                return
            aid = self._resolve_album_id(parts[2])
            if aid is None: return
            info(f"Queuing album {c(aid, CYAN)} as zip...")
            _show_resp(self.client.download(aid, "album", create_zip=True))

        elif sub == "playlist":
            if len(parts) < 3:
                warn("Usage: dl playlist <deezer_url_or_playlist_id>")
                return
            _show_resp(self.client.download_deezer_playlist(parts[2]))

        elif sub == "spotify":
            if len(parts) < 4:
                warn("Usage: dl spotify <playlist_name> <spotify_url>")
                return
            _show_resp(self.client.download_spotify_playlist(parts[2], parts[3]))

        elif sub in ("youtube", "yt"):
            if len(parts) < 3:
                warn("Usage: dl youtube <url>")
                return
            info("Queuing YouTube URL...")
            _show_resp(self.client.download_youtube(parts[2]))

        elif sub == "favorites":
            if len(parts) < 3:
                warn("Usage: dl favorites <deezer_user_id>")
                return
            info(f"Queuing Deezer favorites for user {c(parts[2], CYAN)}...")
            _show_resp(self.client.download_favorites(parts[2]))

        else:
            warn(f"Unknown download type '{sub}'.")
            warn("Options: track | album | zip | playlist | spotify | youtube | favorites")

    def _cmd_queue(self):
        data = self.client.queue()
        sep()
        print(c("  \U0001f4cb  Download queue", BOLD))
        sep()
        if not data:
            print(c("  (queue is empty)", DIM))
        else:
            for task in reversed(data):
                state = str(task.get("state", "?"))
                if "accomplished" in state:
                    sc = GREEN
                elif "active" in state or "working" in state:
                    sc = YELLOW
                elif "failed" in state:
                    sc = RED
                else:
                    sc = DIM
                desc = task.get("description", "?")
                args = task.get("args", "")
                exc  = str(task.get("exception", ""))
                prog = task.get("progress", [0, 0])
                print(f"  {c(desc, BOLD)}  {c(state, sc)}  {c(str(args), DIM)}")
                if prog and prog[1]:
                    bar_len = 28
                    done = int(bar_len * prog[0] / max(prog[1], 1))
                    bar = "\u2588" * done + "\u2591" * (bar_len - done)
                    print(f"    {c(bar, CYAN)} {prog[0]}/{prog[1]}")
                if exc and exc not in ("None", ""):
                    print(f"    {c(exc, RED)}")
        sep()

    def _cmd_debug(self):
        data = self.client.debug()
        msg = data.get("debug_msg", "") if isinstance(data, dict) else str(data)
        sep()
        print(c("  \U0001f41b  Debug log", BOLD))
        sep()
        tail = msg[-3000:] if len(msg) > 3000 else msg
        print(tail)
        sep()

    # ── id resolution ─────────────────────────────────────────────────────────

    def _resolve_track_id(self, arg: str) -> Optional[int]:
        a = arg.lstrip("#")
        if not a.isdigit():
            err(f"Invalid id: {arg!r}  (must be a number or #N)")
            return None
        n = int(a)
        if arg.startswith("#") or n <= len(self._last_tracks):
            if 1 <= n <= len(self._last_tracks):
                t = self._last_tracks[n - 1]
                name = f"{t.get('artist','?')} \u2014 {t.get('title','?')}"
                tid = int(t.get("id"))
                info(f"#{n} \u2192 {c(name, MAGENTA)}  (id={tid})")
                return tid
        return n

    def _resolve_album_id(self, arg: str) -> Optional[int]:
        a = arg.lstrip("#")
        if not a.isdigit():
            err(f"Invalid id: {arg!r}  (must be a number or #N)")
            return None
        n = int(a)
        if arg.startswith("#") or n <= len(self._last_albums):
            if 1 <= n <= len(self._last_albums):
                al = self._last_albums[n - 1]
                name = f"{al.get('artist','?')} \u2014 {al.get('album','?')}"
                aid = int(al.get("album_id") or al.get("id"))
                info(f"#{n} \u2192 {c(name, MAGENTA)}  (album_id={aid})")
                return aid
        return n

    def _resolve_artist_id(self, arg: str) -> Optional[int]:
        a = arg.lstrip("#")
        if not a.isdigit():
            err(f"Invalid id: {arg!r}  (must be a number or #N)")
            return None
        n = int(a)
        if arg.startswith("#") or n <= len(self._last_artists):
            if 1 <= n <= len(self._last_artists):
                ar = self._last_artists[n - 1]
                aid = int(ar.get("artist_id"))
                info(f"#{n} \u2192 {c(ar.get('artist','?'), MAGENTA)}  (artist_id={aid})")
                return aid
        return n


# ── one-shot mode ─────────────────────────────────────────────────────────────

def oneshot_search(client, query):
    print_tracks(client.search(query, "track"))


def oneshot_dl(client, kind, dl_args):
    kind = kind.lower()
    if kind in ("track", "t"):
        _show_resp(client.download(int(dl_args[0]), "track"))
    elif kind in ("album", "a"):
        _show_resp(client.download(int(dl_args[0]), "album"))
    elif kind in ("youtube", "yt"):
        _show_resp(client.download_youtube(dl_args[0]))
    elif kind == "playlist":
        _show_resp(client.download_deezer_playlist(dl_args[0]))
    else:
        err(f"Unknown download type: {kind}")


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="deezer-cli",
        description="Interactive CLI client for deezer-downloader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python deezer_cli.py                              # interactive mode
              python deezer_cli.py --host http://127.0.0.1:5001
              python deezer_cli.py search "Adele Hello"         # search tracks
              python deezer_cli.py dl track 8086130             # download track
              python deezer_cli.py dl album 123456
              python deezer_cli.py dl youtube "https://..."
        """),
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("DEEZER_HOST", "http://localhost:5000"),
        help="Server URL  (env: DEEZER_HOST, default: http://localhost:5000)",
    )
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI colour output")

    sub = parser.add_subparsers(dest="cmd")

    p_s = sub.add_parser("search", help="One-shot track search")
    p_s.add_argument("query", nargs="+")

    p_d = sub.add_parser("dl", help="One-shot download")
    p_d.add_argument("kind", choices=["track","t","album","a","youtube","yt","playlist"])
    p_d.add_argument("dl_args", nargs="+")

    args = parser.parse_args()

    if args.no_color or not sys.stdout.isatty():
        for name in ["RESET","BOLD","DIM","RED","GREEN","YELLOW","MAGENTA","CYAN","WHITE"]:
            globals()[name] = ""

    client = DeezerClient(args.host)

    try:
        if args.cmd == "search":
            oneshot_search(client, " ".join(args.query))
        elif args.cmd == "dl":
            oneshot_dl(client, args.kind, args.dl_args)
        else:
            REPL(client).run()
    except RuntimeError as e:
        err(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
