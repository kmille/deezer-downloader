#!/bin/bash
set -eu

LATEST_DD_TAG=$(git describe --tags --abbrev=0)
LATEST_UBUNTU_TAG_DATE=$(cat Dockerfile | grep ^FROM | cut -d - -f 2)

echo "Dockerhub login"
sudo docker login -u kmille2
sudo docker push "kmille2/deezer-downloader:$LATEST_DD_TAG-$LATEST_UBUNTU_TAG_DATE"
sudo docker push kmille2/deezer-downloader:latest
sudo docker logout

echo "Cleaning up"
sudo docker rmi kmille2/deezer-downloader:latest
sudo docker rmi "kmille2/deezer-downloader:$LATEST_DD_TAG-$LATEST_UBUNTU_TAG_DATE"
sudo docker rmi "ubuntu-$LATEST_UBUNTU_TAG_DATE"
