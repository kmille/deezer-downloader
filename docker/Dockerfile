FROM ubuntu:focal-20211006
MAINTAINER kmille@androidloves.me

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=TRUE

RUN apt-get update -y && \
    apt-get install -y git python3 python3-virtualenv && \
    apt-get install -y --no-install-recommends ffmpeg

RUN git clone https://github.com/kmille/deezer-downloader.git /opt/deezer
RUN python3 -m virtualenv -p python3 /opt/deezer/app/venv
RUN /bin/bash -c "source /opt/deezer/app/venv/bin/activate && \
                  pip install -r /opt/deezer/requirements.txt && \
                  pip install -U yt-dlp \
                  pip install gunicorn"

RUN cp /opt/deezer/app/settings.ini.example /opt/deezer/app/settings.ini
RUN sed -i 's,.*command = /usr/bin/yt-dlp.*,command = /opt/deezer/app/venv/bin/yt-dlp,' /opt/deezer/app/settings.ini
RUN sed -i 's,/tmp/deezer-downloader,/mnt/deezer-downloader,' /opt/deezer/app/settings.ini

RUN useradd -s /bin/bash deezer
RUN mkdir -p /mnt/deezer-downloader
RUN chown deezer:deezer /mnt/deezer-downloader

USER deezer
EXPOSE 5000
WORKDIR /opt/deezer/app
CMD /opt/deezer/app/venv/bin/gunicorn --bind 0.0.0.0:5000 app:app
