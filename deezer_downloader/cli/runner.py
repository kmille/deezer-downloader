#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
import waitress


def run_backend():
    from deezer_downloader.configuration import config
    from deezer_downloader.web.app import app

    print(f"Listening on {config['http']['host']}:{config['http'].getint('port')}")
    if __name__ == '__main__':
        app.run(debug=True,
                host=config['http']['host'],
                port=config['http'].getint('port'))
    else:
        listen = f"{config['http']['host']}:{config['http'].getint('port')}"
        waitress.serve(app, listen=listen)


def main():
    parser = argparse.ArgumentParser(prog='deezer-downloader',
                                     description="Download music from Deezer and Spotify with a simple web frontend, through a local-hosted service written in Python.",
                                     epilog="More info at https://github.com/kmille/deezer-downloader.")
    parser.add_argument("-v", "--version", action='store_true', help="show version and exit")
    parser.add_argument("-t", "--show-config-template", action='store_true', help="show config template - you have to provide the ARL cookie at least")
    parser.add_argument("-c", "--config", help="config file - if not supplied, the following directories are considered looking for deezer-downloader.ini: current working directory, XDG_CONFIG_HOME environment variable, ~/.config, /etc)")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    if args.version:
        from importlib.metadata import version
        v = version("deezer_downloader")
        print(sys.argv[0], f"v{v}")
        sys.exit(0)

    if args.show_config_template:
        print((Path(__file__).parent / Path("deezer-downloader.ini.template")).read_text(), end="")
        sys.exit(0)

    from deezer_downloader.configuration import load_config
    load_config(args.config)
    run_backend()


if __name__ == '__main__':
    main()
