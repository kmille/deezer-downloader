# Simple web app writting in flask for downloading songs/albums/playlists from deezer.com
- a Deezer account is required (free plan)
- download Spotify playlists (it just will parse the Spotify playlist and search for each song on Deezer and download it from there)
- download songs with youtube-dl
- integrated to mpd for full enjoyment
- you can choose between: just download it, download it and queue it to mpd, download it as zip


# Deployment
```
virtualenv -p python3 venv
source venv/bin/activate
pip install -r requirements.txt
cd app
insert your sid cookie value to to credentials.py (login manually using your web browser and take the sid cookie; begins with fr...)
python app.py


# Add systemd timer which regularly sends a request to deezer 
# if you don't use it: the cookie will expire and we are getting logged out
cd systemd/
sudo cp deezer-stay-loggedin.service /etc/systemd/system
sudo cp deezer-stay-loggedin.timer /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable deezer-stay-loggedin.timer
sudo systemctl start deezer-stay-loggedin.timer
sudo systemctl list-timers | grep deezer

```

# Unittests
python -m unittest -f tests.py  
Because of [this](https://github.com/general03/flask-autoindex/issues/53])  we use an old version of Werkzeug   


# Usage
You can specify the download dir in the settings.py (download_dir). Pressing the download button only downloads the song/album. If you set update_mpd=True in the settings.py the backend will connect to mpd (localhost:6600) and update the music database. Pressing the play button will download the music. If update_mpd=True the mpd database will be updated and the song/album will be added to the playlist. In settings.py music_dir should be the root of the music for mpd. The download_dir is a directory in the music_dir. Both directories should not end with a trailing slash.

# Shortcuts
ctrl-m: focus search bar  
Enter: serach for songs  
Alt+Enter: search for albums  
ctrl-b: go to / (this is where our ympd is)  
ctrl-shift-[1-6] switch tabs  

# Disclaimer
I'm not responsible for deezer.py (the actual download code). This is the ugliest code I've ever seen.

# Deployment with ansible (includig mpd and ympd)
https://github.com/kmille/music-ansible (almost always outdated)

# Some screenshots
![](/screenshots/2020-03-11-111518_screenshot.png)  
  
![](/screenshots/2020-03-11-111526_screenshot.png)  
  
![](/screenshots/2020-03-11-111531_screenshot.png)  
  
![](/screenshots/2020-03-11-111546_screenshot.png)  
  
