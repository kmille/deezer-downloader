import sys
import os
import os.path
from configparser import ConfigParser

config_file = "settings.ini"
config_abs = os.path.join(os.path.dirname(os.path.realpath(__file__)), config_file)

if not os.path.exists(config_abs):
    print(f"Could not find config file ({config_abs}). You can move the template")
    sys.exit(1)

config = ConfigParser()
config.read(config_abs)

assert list(config.keys()) == ['DEFAULT', 'mpd', 'download_dirs', 'debug', 'http', 'threadpool', 'deezer', 'youtubedl'], f"Validating settings.ini failed. Check {__file__}"

if config['mpd'].getboolean('use_mpd'):
    if not config['mpd']['music_dir_root'].startswith(config['download_dirs']['base']):
        print("ERROR: base download dir must be a subdirectory of the mpd music_dir_root")
        sys.exit(1)

if not os.path.exists(config['youtubedl']['command']):
    print(f"ERROR: youtube-dl not found at {config['youtubedl']['command']}")
    sys.exit(1)

if "DEEZER_COOKIE_ARL" in os.environ.keys():
    config["deezer"]["cookie_arl"] = os.environ["DEEZER_COOKIE_ARL"]

if len(config["deezer"]["cookie_arl"].strip()) == 0:
    print("ERROR: cookie_arl must not be empty")
    sys.exit(1)
