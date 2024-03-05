#!/bin/bash
set -eu

VERSION="v$(poetry version -s)"
echo sudo docker build --no-cache --force-rm . --file Dockerfile --tag kmille2/deezer-downloader
echo sudo docker tag kmille2/deezer-downloader "kmille2/deezer-downloader:$VERSION"
echo sudo docker tag kmille2/deezer-downloader kmille2/deezer-downloader:latest
