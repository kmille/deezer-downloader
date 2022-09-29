#!/bin/bash
set -eu

CURRENT_UBUNTU_TAG=$(cat Dockerfile | grep ^FROM | cut -d : -f 2)

# TODO: this is broken
#LATEST_UBUNTU_TAG=$(wget -q https://registry.hub.docker.com/v1/repositories/ubuntu/tags -O -  | sed -e 's/[][]//g' -e 's/"//g' -e 's/ //g' | tr '}' '\n'  | awk -F: '{print $3}' | grep ^focal | sort -V | tail -n 1)
LATEST_UBUNTU_TAG=focal-20220826

LATEST_UBUNTU_TAG_DATE=$(echo $LATEST_UBUNTU_TAG | cut -d - -f 2)
LATEST_DD_TAG=$(git describe --tags --abbrev=0)

echo "Current ubuntu tag: $CURRENT_UBUNTU_TAG"
echo "Latest ubuntu tag:  $LATEST_UBUNTU_TAG (date=$LATEST_UBUNTU_TAG_DATE)"

echo -n "Update image (y/n)? "
read answer
if [ "$answer" != "${answer#[Yy]}" ]
then
    sed -i "s/^FROM.*/FROM ubuntu:$LATEST_UBUNTU_TAG/" Dockerfile
    sudo docker build --no-cache --force-rm . --file Dockerfile --tag kmille2/deezer-downloader
    sudo docker tag kmille2/deezer-downloader "kmille2/deezer-downloader:$LATEST_DD_TAG-$LATEST_UBUNTU_TAG_DATE"
    sudo docker tag kmille2/deezer-downloader kmille2/deezer-downloader:latest
    git diff
else
    exit 0
fi
