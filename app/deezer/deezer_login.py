import requests
from ipdb import set_trace
import os.path
import pickle
from credentials import email, password

pickle_file = "session.pickle"
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
        if os.path.exists(pickle_file):
            self.session.cookies = pickle.load(open(pickle_file))

    def get_csrf_token(self):
        self.session.get(base % "/login")
        resp = self.session.post(base % "/ajax/gw-light.php?method=deezer.getUserData&input=3&api_version=1.0&api_token=&cid=")
        return resp.json()['results']['checkFormLogin']
    
    def login(self):
        print("Do the login")
#        data = { 'type':'login',
#                 'mail': email,
#                 'password': password,
#                 'checkFormLogin': self.get_csrf_token()
#                }
#        resp = self.session.post(base % "/ajax/action.php", data=data)
        self.session.cookies.clear()
        self.session.cookies.update({'sid': 'fr019cf438642a7378aec18e8d101b92db73cb68', 'comeback':'1'})
        return self.test_login()

    def test_login(self):
        resp = self.session.get(base % "/us/artist/542")
        login_successfull =  "MD5_ORIGIN" in resp.text
        if login_successfull:
            #print("Dumping cookies for later use")
            pickle.dump(self.session.cookies, open(pickle_file, "wb"))
        else:
            print("Login was not successfull")
        return login_successfull

    
if __name__ == '__main__':
    DeezerLogin()
