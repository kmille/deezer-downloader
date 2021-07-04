# Pull git base image for downloading the repo.
FROM alpine/git:latest
MAINTAINER kmille@androidloves.me

RUN git clone https://github.com/kmille/deezer-downloader.git /opt/deezer

# Pull base image for python.
FROM python:3.8-slim

# Set the working directory for the app.
WORKDIR /opt/app
COPY --from=0 /opt/deezer/ /opt/deezer/

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=TRUE

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends ffmpeg && \
    pip3 install virtualenv && \
    python3 -m virtualenv -p python3 /opt/deezer/app/venv && \
    /bin/bash -c "source /opt/deezer/app/venv/bin/activate && \
                  pip install -r /opt/deezer/requirements.txt && \
                  pip install -U youtube-dl \
                  pip install gunicorn" && \
    cp /opt/deezer/app/settings.ini.example /opt/deezer/app/settings.ini && \
    sed -i 's,.*command = /usr/bin/youtube-dl.*,command = /opt/deezer/app/venv/bin/youtube-dl,' /opt/deezer/app/settings.ini && \
    sed -i 's,/tmp/deezer-downloader,/mnt/deezer-downloader,' /opt/deezer/app/settings.ini && \
    useradd -s /bin/bash deezer && \
    mkdir -p /mnt/deezer-downloader && \
    chown deezer:deezer /mnt/deezer-downloader && \
    apt autoremove --purge && \
    apt autoremove && \
    apt clean && \
    rm -rf /var/lib/apt

USER deezer
EXPOSE 5000
WORKDIR /opt/deezer/app
CMD /opt/deezer/app/venv/bin/gunicorn --bind 0.0.0.0:5000 app:app
