import sys
import requests
from ipdb import set_trace
import os.path
import pickle
from credentials import sid

base = "https://www.deezer.com%s"
header = {
    'Pragma': 'no-cache' ,
    'Origin': 'https://www.deezer.com' ,
    'Accept-Encoding': 'gzip, deflate, br' ,
    'Accept-Language': 'en-US,en;q=0.9' ,
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36' ,
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' ,
    'Accept': '*/*' ,
    'Cache-Control': 'no-cache' ,
    'X-Requested-With': 'XMLHttpRequest' ,
    'Connection': 'keep-alive' ,
    'Referer': 'https://www.deezer.com/login' ,
    'DNT': '1' ,
    }

class DeezerLogin():

    def __init__(self):
        self.session = requests.session()
        self.session.headers.update(header)
        self.session.cookies.update({'sid': sid, 'comeback':'1'})

    def test_login(self):
        # sid cookie has no expire date. Session will be extended on the server side
        # so we will just send a request regularly to not get logged out
        resp = self.session.get(base % "/us/artist/542")
        login_successfull =  "MD5_ORIGIN" in resp.text
        if login_successfull:
            print("Login is still working.")
        else:
            print("Login is not working anymore.")
        return not login_successfull

    
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "test_login":
        sys.exit(DeezerLogin().test_login())
    else:
        DeezerLogin()
