FROM debian:buster-20200514
MAINTAINER kmille@androidloves.me

RUN apt-get update  -yq && \
    apt-get install -yq vim tmux git gcc ffmpeg \ 
                        python3-virtualenv python3-dev \
                        mpd ncmpcpp
RUN git clone https://github.com/kmille/deezer-downloader.git /opt/deezer
RUN python3 -m virtualenv -p python3 /opt/deezer/app/venv
RUN /bin/bash -c "source /opt/deezer/app/venv/bin/activate && \
    pip install -r /opt/deezer/requirements.txt && \
    pip install -U youtube-dl"
RUN cp /opt/deezer/app/settings.ini.example /opt/deezer/app/settings.ini
RUN sed -i 's/.*host = 127.0.0.1.*/host = 0.0.0.0/' /opt/deezer/app/settings.ini
RUN sed -i 's,.*command = /usr/bin/youtube-dl.*,command = /opt/deezer/app/venv/bin/youtube-dl,' /opt/deezer/app/settings.ini
RUN sed -i 's,.*command = /usr/bin/youtube-dl.*,command = /opt/deezer/app/venv/bin/youtube-dl,' /opt/deezer/app/settings.ini
RUN sed -i 's,/tmp/deezer-downloader,/mnt/deezer-downloader,' /opt/deezer/app/settings.ini

RUN useradd -s /bin/bash deezer
RUN chown -R deezer /opt/deezer

USER deezer
EXPOSE 5000
CMD /opt/deezer/app/venv/bin/python -u /opt/deezer/app/app.py
