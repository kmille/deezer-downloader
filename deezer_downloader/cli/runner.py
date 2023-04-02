#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
import waitress


def run_backend():
    from deezer_downloader.configuration import config
    from deezer_downloader.web.app import app

    listen = f"{config['http']['host']}:{config['http'].getint('port')}"
    waitress.serve(app, listen=listen)


def main():
    parser = argparse.ArgumentParser(prog='deezer-downloader',
                                     description="Download music from Deezer with a nice front end")
    parser.add_argument("-v", "--version", action='store_true', help="show version and exit")
    parser.add_argument("-t", "--show-config-template", action='store_true', help="show config template. At least you have to insert the ARL cookie")
    parser.add_argument("-c", "--config", help="config file - if not supplied, the following directories are considered looking for deezer-downloader.ini: current working directory, XDG_CONFIG_HOME environment variable, ~/.config, /etc)")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    if args.version:
        from deezer_downloader import __version__
        print(sys.argv[0], f"v{__version__}")
        sys.exit(0)

    if args.show_config_template:
        print((Path(__file__).parent / Path("deezer-downloader.ini.template")).read_text(), end="")
        sys.exit(0)

    from deezer_downloader.configuration import load_config
    load_config(args.config)
    run_backend()


if __name__ == '__main__':
    main()
