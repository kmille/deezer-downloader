# Simple web app writting in flask for downloading songs/albums from deezer.com
- a Deezer account is required (free plan)
- earlier versions of this tool logged in manually and dumped the session
- after Deezer now uses a captcha during the login: login manually in the browser and get the sid cookie

# Deployment
```
python2 -m virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
cd app
insert your sid cookie value to to app/credentials.py
python app.py


# Add systemd timer which regularly sends a request to deezer 
# the backend will extend our session
cd systemd/
cp deezer-stay-loggedin.service /etc/systemd/system
cp deezer-stay-loggedin.timer /etc/systemd/system
systemctl daemon-reload
systemctl enable deezer-stay-loggedin.timer
systemctl start deezer-stay-loggedin.timer
systemctl list-timers | grep deezer

```

# Usage
You can specify the download dir in the settings.py (download_dir). Pressing the download button only downloads the song/album. If you set update_mpd=True in the settings.py the backend will connect to mpd (localhost:6600) and update the music database. Pressing the play button will download the music. If update_mpd=True the mpd database will be updated and the song/album will be added to the playlist. In settings.py music_dir should be the root of the music for mpd. The download_dir is a directory in the music_dir. Both directories should not end with a trailing slash.

# Shortcuts
ctrl-m: focus search bar  
Enter: serach for songs  
Alt+Enter: search for albums  
cbtrl-b: go to / (this is where our ympd is)  

# Disclaimer
I'm not responsible for deezer.py (the actual download code). This is the ugliest code I've ever seen.

# Deployment with ansible (includig mpd and ympd)
https://github.com/kmille/music-ansible

# Screenshot
![Alt text](https://image.ibb.co/cjBC30/screen.png "KISS")
