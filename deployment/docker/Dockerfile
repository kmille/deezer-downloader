FROM ubuntu:jammy-20230308
MAINTAINER kmille@androidloves.me

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=TRUE

RUN apt-get update -y && \
    apt-get install -y python3-pip && \
    apt-get install -y --no-install-recommends ffmpeg

RUN pip install deezer-downloader

RUN /usr/local/bin/deezer-downloader --show-config-template > /etc/deezer-downloader.ini && \
     sed -i "s,.*command = /usr/bin/yt-dlp.*,command = $(which yt-dlp)," /etc/deezer-downloader.ini && \
     sed -i 's,host = 127.0.0.1,host = 0.0.0.0,' /etc/deezer-downloader.ini && \
     sed -i 's,/tmp/deezer-downloader,/mnt/deezer-downloader,' /etc/deezer-downloader.ini

RUN useradd -s /bin/bash deezer
RUN mkdir -p /mnt/deezer-downloader
RUN chown deezer:deezer /mnt/deezer-downloader

USER deezer
EXPOSE 5000
CMD /usr/local/bin/deezer-downloader --config /etc/deezer-downloader.ini
