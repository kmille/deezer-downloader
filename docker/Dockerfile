# Pull git base image for downloading the repo.
FROM alpine/git:latest
MAINTAINER kmille@androidloves.me

RUN git clone https://github.com/kmille/deezer-downloader.git /opt/deezer

# Pull base image for python.
FROM python:3.8-alpine3.14

# Set the working directory for the app.
WORKDIR /opt/app
COPY --from=0 /opt/deezer/ /opt/deezer/

ENV PYTHONUNBUFFERED=TRUE

RUN apk add --no-cache ffmpeg alpine-sdk autoconf automake libtool gcc g++ make libffi-dev openssl-dev && \
    pip3 install --upgrade setuptools && \
    pip3 install virtualenv && \
    python3 -m virtualenv -p python3 /opt/deezer/app/venv && \
    /bin/sh -c "source /opt/deezer/app/venv/bin/activate && \
                  pip install --no-cache-dir -r /opt/deezer/requirements.txt && \
                  pip install --no-cache-dir -U youtube-dl \
                  pip install --no-cache-dir gunicorn" && \
    cp /opt/deezer/app/settings.ini.example /opt/deezer/app/settings.ini && \
    sed -i 's,.*command = /usr/bin/youtube-dl.*,command = /opt/deezer/app/venv/bin/youtube-dl,' /opt/deezer/app/settings.ini && \
    sed -i 's,/tmp/deezer-downloader,/mnt/deezer-downloader,' /opt/deezer/app/settings.ini && \
    adduser -D -s /bin/sh deezer && \
    mkdir -p /mnt/deezer-downloader && \
    chown deezer:deezer /mnt/deezer-downloader && \
    apk del alpine-sdk autoconf automake libtool gcc g++ make libffi-dev openssl-dev && \
    rm -rf /var/cache/apk/*

USER deezer
EXPOSE 5000
WORKDIR /opt/deezer/app
CMD /opt/deezer/app/venv/bin/gunicorn --bind 0.0.0.0:5000 app:app
