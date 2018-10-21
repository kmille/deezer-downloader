from __future__ import unicode_literals
from ipdb import set_trace
import youtube_dl


ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    #'outtmpl': '/tmp/foo_%(title)s-%(id)s.%(ext)s'

    }],
}
with youtube_dl.YoutubeDL(ydl_opts) as ydl:
    set_trace()
    ydl.download(['http://www.youtube.com/watch?v=BaW_jenozKc'])
