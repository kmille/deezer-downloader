#!/bin/bash
set -eu

DD_VERSION="v$(poetry version -s)"
# get 'alpine3.21' from 'FROM python:3.12-alpine3.21 AS builder'
ALPINE_VERSION=$(tac Dockerfile | grep -m 1 ^FROM | cut -d - -f 2)

echo "Dockerhub login"
# sudo docker login -u kmille2

sudo docker push "kmille2/deezer-downloader:$DD_VERSION-$ALPINE_VERSION"
sudo docker push kmille2/deezer-downloader:latest
# sudo docker logout

echo "Cleaning up"
sudo docker rmi kmille2/deezer-downloader:latest
sudo docker rmi "kmille2/deezer-downloader:$DD_VERSION-$ALPINE_VERSION"
