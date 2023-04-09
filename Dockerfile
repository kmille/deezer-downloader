FROM python:3.10-alpine3.17 AS builder
RUN pip install poetry
COPY . /app
WORKdir /app
RUN poetry build --format=wheel


FROM python:3.10-alpine3.17
ENV PYTHONUNBUFFERED=TRUE

COPY --from=builder /app/dist/deezer_downloader*.whl .

RUN apk add --no-cache ffmpeg && \
    adduser -D deezer && \
    mkdir -p /mnt/deezer-downloader && \
    chown deezer:deezer /mnt/deezer-downloader

RUN pip install deezer_downloader*.whl && \
    /usr/local/bin/deezer-downloader --show-config-template > /etc/deezer-downloader.ini && \
    sed -i "s,.*command = /usr/bin/yt-dlp.*,command = $(which yt-dlp)," /etc/deezer-downloader.ini && \
    sed -i 's,host = 127.0.0.1,host = 0.0.0.0,' /etc/deezer-downloader.ini && \
    sed -i 's,/tmp/deezer-downloader,/mnt/deezer-downloader,' /etc/deezer-downloader.ini && \
    rm deezer_downloader*.whl

USER deezer
EXPOSE 5000
ENTRYPOINT ["/usr/local/bin/deezer-downloader", "--config", "/etc/deezer-downloader.ini"]
