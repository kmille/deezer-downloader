# Simple web app writting in flask for downloading songs/albums from deezer.com
- a valid Deezer login credentials are required (free plan)

Update April 2019:  
The login is broken as Deezer now uses a Google Captcha for the login. Quick fix: login manually in the browser and copy the cookie:
Quick fix patch  
```diff
diff --git a/app/deezer/deezer_login.py b/app/deezer/deezer_login.py
index 7e28650..6df65df 100644
--- a/app/deezer/deezer_login.py
+++ b/app/deezer/deezer_login.py
@@ -36,12 +36,14 @@ class DeezerLogin():
     
     def login(self):
         print("Do the login")
-        data = { 'type':'login',
-                 'mail': email,
-                 'password': password,
-                 'checkFormLogin': self.get_csrf_token()
-                }
-        resp = self.session.post(base % "/ajax/action.php", data=data)
+#        data = { 'type':'login',
+#                 'mail': email,
+#                 'password': password,
+#                 'checkFormLogin': self.get_csrf_token()
+#                }
+#        resp = self.session.post(base % "/ajax/action.php", data=data)
+        self.session.cookies.clear()
+        self.session.cookies.update({'sid': 'fr019cf438642a7378aec18e8d101b92db73cb68', 'comeback':'1'})
         return self.test_login()
 
     def test_login(self):
```





# Deployment
```
python2 -m virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
cd app
insert your deezer credentials to app/credentials.py
python app.py
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
