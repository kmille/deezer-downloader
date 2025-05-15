FROM python:3.12-alpine3.21 AS builder
RUN pip install poetry
COPY . /app
WORKDIR /app
RUN poetry build --format=wheel


FROM python:3.12-alpine3.21
ENV PYTHONUNBUFFERED=TRUE

RUN apk add --no-cache ffmpeg && \
    adduser -D deezer && \
    mkdir -p /mnt/deezer-downloader && \
    chown deezer:deezer /mnt/deezer-downloader

COPY --from=builder /app/dist/deezer_downloader*.whl .
RUN pip install deezer_downloader*.whl && \
    /usr/local/bin/deezer-downloader --show-config-template > /etc/deezer-downloader.ini && \
    sed -i "s,.*command = /usr/bin/yt-dlp.*,command = $(which yt-dlp)," /etc/deezer-downloader.ini && \
    sed -i 's,host = 127.0.0.1,host = 0.0.0.0,' /etc/deezer-downloader.ini && \
    sed -i 's,/tmp/deezer-downloader,/mnt/deezer-downloader,' /etc/deezer-downloader.ini && \
    rm deezer_downloader*.whl

ENV LOG_FILE=/tmp/deezer-downloader.log

USER deezer
EXPOSE 5000
CMD /bin/sh -c "/usr/local/bin/deezer-downloader --config /etc/deezer-downloader.ini | tee $LOG_FILE"
