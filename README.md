## Music Downloader  :notes: :headphones: :dancer: :unicorn:
![tests](https://github.com/kmille/deezer-downloader/workflows/tests/badge.svg) ![push image to dockerhub](https://github.com/kmille/deezer-downloader/workflows/push%20to%20dockerhub/badge.svg) ![docker pulls](https://img.shields.io/docker/pulls/kmille2/deezer-downloader) ![latest tag](https://img.shields.io/github/v/tag/kmille/deezer-downloader?sort=semver) ![Python 3.6](https://img.shields.io/badge/python-%3E=3.6-blue.svg)


### Features

- download songs, albums, public playlists from Deezer.com (account is required, free plan is enough)
- download Spotify playlists (by parsing the Spotify website and download the songs from Deezer)
- download as zip file (including m3u8 playlist file)
- 320 kbit/s mp3s with ID3-Tags and album cover (UPDATE: right now only 128bkit/s mp3 works, see #66)
- download songs via youtube-dl
- KISS front end
- MPD integration (use it on a Raspberry Pi!)
- simple REST api



### How to use it

There is a settings file template called `settings.ini.example`. You can specify the download directory with  `download_dir`. Pressing the download button only downloads the song/album/playlist. If you set `use_mpd=True` in the `settings.ini` the backend will connect to mpd (localhost:6600) and update the music database. Pressing the play button will download the music. If `use_mpd=True`  is set the mpd database will be updated and the song/album/playlist will be added to the playlist. In `settings.ini` `music_dir` should be the music root location of mpd. The `download_dir` must be a subdirectory of `music_dir`. 

As Deezer sometimes requires a captcha to login the auto login features was removed. Instead you have to manually insert a valid Deezer cookie to the `settings.ini`. The relevant cookie is the `arl` cookie. 



### Run it as a service

We use it with nginx and [ympd](https://github.com/notandy/ympd) as mpd frontend

- / goes to ympd
- /d/ goes to the downloader

The deployment directory contains a systemd unit file and a nginx vhost config file. There is also a [patch](https://github.com/kmille/music-ansible/blob/master/roles/ympd/files/fix_header.patch) to add a link to the ympd frontend. The `debug` tab will show you the debug output of the app.



### Try it out

```bash	
vagrant up
vagrant ssh
sudo vim /opt/deezer/app/settings.ini # insert your Deezer cookie
/opt/deezer/app/venv/bin/python /opt/deezer/app/app.py # start the backend

# On the host:
xdg-open http://localhost:5000 # view frontend in the browser
ncmpcpp -h 127.0.0.1 # try the mpd client
```

### Docker

You can use the Docker image hosted on [hub.docker.com](https://hub.docker.com/r/kmille2/deezer-downloader). Login into your free Deezer account and grab the `arl` cookie. Then:

```bash
mkdir downloads
sudo docker run -p 5000:5000 --volume $(pwd)/downloads/:/mnt/deezer-downloader --env DEEZER_COOKIE_ARL=changeme --env DEEZER_FLAC_QUALITY=True kmille2/deezer-downloader:latest 
xdg-open http://localhost:5000
```

If you want to debug or build it from source: there is a docker-compose file in the docker directory. The `docker/downloads` directory is mounted into the container and will be used as download directory. You have to check the permissions of the `docker/downloads` directory as docker mounts it with the same owner/group/permissions as on the host. The `deezer` user in the docker container has uid 1000. If you also have the uid 1000 then there should be no problem. For debugging: `sudo docker-compose build --force-rm && sudo docker-compose up`

### Deployment

```bash
apt-get update -q
apt-get install -qy vim tmux git gcc ffmpeg
apt-get install -qy python3-virtualenv python3-dev
git clone https://github.com/kmille/deezer-downloader.git /opt/deezer
python3 -m virtualenv -p python3 /opt/deezer/app/venv
source /opt/deezer/app/venv/bin/activate
pip install -r /opt/deezer/requirements.txt
pip install -U youtube-dl
cp /opt/deezer/app/settings.ini.example /opt/deezer/app/settings.ini
# Adjust /opt/deezer/app/settings.ini
/opt/deezer/app/venv/bin/python /opt/deezer/app/app.py

# for mpd
apt-get install -yq mpd ncmpcpp
# adjust the file paths in /etc/mpd.conf and settings.ini
systemctl restart mpd
ncmpcpp -h 127.0.0.1
```



### Shortcuts
ctrl-m: focus search bar  
Enter: serach for songs   
Alt+Enter: search for albums  
ctrl-b: go to / (this is where our ympd is)  
ctrl-shift-[1-7] switch tabs    



### Some screenshots

Search for songs. You can listen to a 30 second preview in the browser.  

![](/screenshots/2020-05-13-211356_screenshot.png)  

Search for albums. You can download them as zip file.  

![](/screenshots/2020-05-13-213544_screenshot.png)

List songs of an album.

![](/screenshots/2020-05-13-211528_screenshot.png)

Download songs with youtube-dl  

![](/screenshots/2020-05-13-211622_screenshot.png)

Download a Spotify playlist.   

![](/screenshots/2020-05-13-211629_screenshot.png)  

Download a Deezer playlist.    

![](/screenshots/2020-05-13-211633_screenshot.png)  

ncmpcpp mpd client.  

![](/screenshots/2020-05-13-212025_screenshot.png)  



### Tests

```bash
cd app
source venv/bin/activate
python -m pytest -v tests.py
```



### Deployment with Ansible (including mpd and ympd)
https://github.com/kmille/music-ansible (almost always outdated)



### Changelog

#### Version 1.3.2 (26.11.2021)
- fix broken deezer download functionality (#66, removes the ability to download flac quality)
- update third party dependencies
- update ubuntu base image for the docker container

#### Version 1.3.1 (21.01.2021)
- allow to set download quality (flac|mp3) via environment variable DEEZER_FLAC_QUALITY (#43)

#### Version 1.3 (05.11.2020)

- feature: download your favorite Deezer songs
- automated tests with Github Actions
- push Docker image to [hub.docker.com](https://hub.docker.com/repository/docker/kmille2/deezer-downloader/general) with Github Actions

#### Version 1.2 (01.11.2020)

- **breaking change:** now use the `arl` cookie instead of the `sid` cookie. This cookie does not expire so we don't need the background thread that keeps the session alive
- add support for flac as download format

#### Version 1.1 (13.05.2020)

- thanks to [luelista](https://github.com/luelista) for the contribution!
- play 30 second preview in browser
- add Vagrantfile
- show album cover in search results
- use a threaded queue for download tasks
- list album songs
