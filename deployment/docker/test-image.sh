#!/bin/bash
set -eu

DEEZER_COOKIE_ARL=changeme

sudo docker kill deezer-downloader 2>&1 >/dev/null || true
sudo docker rm deezer-downloader 2>&1 >/dev/null || true
echo "Running deezer downloader in the background"
sudo docker run -d --name deezer-downloader -p 5000:5000 --volume $(pwd)/downloads/:/mnt/deezer-downloader \
                --env DEEZER_COOKIE_ARL=$DEEZER_COOKIE_ARL "kmille2/deezer-downloader:latest" >/dev/null
sleep 5


## testing deezer
rm -rf 'downloads/songs/Deichkind - Illegale Fans.mp3'
echo "Downloading deezer song"
curl -s --fail 'http://localhost:5000/download' --data-raw '{"type":"track","music_id":82120546,"add_to_playlist":false,"create_zip":false}' >/dev/null
sleep 5
ls -lh 'downloads/songs/Deichkind - Illegale Fans.mp3'
file 'downloads/songs/Deichkind - Illegale Fans.mp3'
rm 'downloads/songs/Deichkind - Illegale Fans.mp3'

## testing youtube-dl
rm -rf 'downloads/youtube-dl/Stereoact feat. Kerstin Ott - Die Immer Lacht (Official Video HD).mp3'
echo "Downloading a song via youtube-dl"
curl -s --fail 'http://localhost:5000/youtubedl' --data-raw '{"url":"https://www.youtube.com/watch?v=Bkj3IVIO2Os","add_to_playlist":false}' >/dev/null
sleep 20
ls -lh 'downloads/youtube-dl/Stereoact feat. Kerstin Ott - Die Immer Lacht (Official Video HD).mp3'
file 'downloads/youtube-dl/Stereoact feat. Kerstin Ott - Die Immer Lacht (Official Video HD).mp3'
rm 'downloads/youtube-dl/Stereoact feat. Kerstin Ott - Die Immer Lacht (Official Video HD).mp3'

echo "remove container/image?"
read

# cleanup
echo "Cleaning up"
sudo docker kill deezer-downloader >/dev/null
sudo docker rm deezer-downloader >/dev/null
