#!/bin/bash
set -eu

# This needs to be run from the project root directory!
# ./deployment/docker/create-docker-image.sh

DD_VERSION="v$(poetry version -s)"
# get 'alpine3.21' from 'FROM python:3.12-alpine3.21 AS builder'
ALPINE_VERSION=$(tac Dockerfile | grep -m 1 ^FROM | cut -d - -f 2)

sudo docker build --no-cache --force-rm . --file Dockerfile --tag kmille2/deezer-downloader
sudo docker tag kmille2/deezer-downloader "kmille2/deezer-downloader:$DD_VERSION-$ALPINE_VERSION"
sudo docker tag kmille2/deezer-downloader kmille2/deezer-downloader:latest
sudo docker tag kmille2/deezer-downloader "ghcr.io/kmille/deezer-downloader:$DD_VERSION-$ALPINE_VERSION"
sudo docker tag kmille2/deezer-downloader ghcr.io/kmille/deezer-downloader:latest
