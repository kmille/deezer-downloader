# API Endpoints

**GET /debug**
- Description: Returns recent debug output (tail of log or configured debug command).
- Parameters: none
- Response: JSON: {"debug_msg": "..."}


**GET /queue**
- Description: Shows queued/background tasks and their status
- Parameters: none
- Response: JSON array of task objects

**POST /search**
- Description: Search Deezer for matching music
- Request JSON body:
  - `type` (string): one of `track`, `album`, `album_track`, `artist`, `artist_album`, `artist_top`
  - `query` (string): search query (non-empty)
- Response: JSON array of search results (artist, id, title/album)

**POST /download**
- Description: Download a Deezer track or album and optionally add to playlist / zip
- Request JSON body:
  - `type` (string): `album` or `track`
  - `music_id` (int): id of the album or track
  - `add_to_playlist` (bool)
  - `create_zip` (bool)
- Response: JSON: {"task_id": <integer>}

**POST /youtubedl**
- Description: Download a media URL using youtube-dl and optionally add to playlist
- Request JSON body:
  - `url` (string): http(s) url supported by youtube-dl
  - `add_to_playlist` (bool)
- Response: JSON: {"task_id": <integer>}

**POST /playlist/deezer**
- Description: Download all songs from a public Deezer playlist
- Request JSON body:
  - `playlist_url` (string): Deezer playlist URL or id
  - `add_to_playlist` (bool)
  - `create_zip` (bool)
- Response: JSON: {"task_id": <integer>}

**POST /playlist/spotify**
- Description: Parse a Spotify playlist, find songs on Deezer and download them
- Request JSON body:
  - `playlist_name` (string): friendly name for the created folder
  - `playlist_url` (string): Spotify playlist URL or id
  - `add_to_playlist` (bool)
  - `create_zip` (bool)
- Response: JSON: {"task_id": <integer>}

**POST /favorites/deezer**
- Description: Download favorite songs of a Deezer user
- Request JSON body:
  - `user_id` (string): numeric Deezer user id (string of digits)
  - `add_to_playlist` (bool)
  - `create_zip` (bool)
- Response: JSON: {"task_id": <integer>}
