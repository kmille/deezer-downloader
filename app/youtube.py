import re
import os.path
from shellescape import quote
from subprocess import Popen, PIPE

from deezer import mpd_update
from settings import music_dir, download_dir
from ipdb import set_trace

youtube_dl_cmd = "youtube-dl -x --audio-format mp3 --audio-quality 0 {video_url} -o '{destination_dir}/%(title)s.%(ext)s'"


def youtubedl_download(url, add_to_playlist):
    video_url = quote(url)
    cmd = youtube_dl_cmd.format(video_url=video_url, destination_dir=download_dir)
    song = execute(cmd)
    mpd_update([song], add_to_playlist=add_to_playlist)


def execute(cmd):
    print("Executing '{}'".format(cmd))
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    p.wait()
    stdout, stderr = p.communicate()
    #print(stdout)
    #print(stderr)
    if p.returncode != 0:
        raise Exception("youtube-dl exited with non-zero: \n{}".format(stderr))
    return get_filename_relative_to_mpd(stdout, stderr)


def get_filename_relative_to_mpd(stdout, stderr):
    regex_foo = re.search(r'Destination:\s(.*mp3)', stdout)
    if not regex_foo:
        raise Exception("EROR: Can not extract output file via regex. \nstderr: {}\nstdout: {}".format(stderr, stderr))
    output_file_absolute = regex_foo.group(1)
    #print("Absolute filename: {}".format(output_file_absolute))

    # prepare for ugly code:
    filename = os.path.basename(output_file_absolute)
    output_file_relative_to_mpd_root = os.path.join(download_dir[len(music_dir)+1:], filename)
    # sry for that

    #print("Filename relative to mpd root: {}".format(output_file_relative_to_mpd_root))
    return output_file_relative_to_mpd_root


if __name__ == '__main__':
    video_url = "https://www.invidio.us/watch?v=ZbZSe6N_BXs"
    youtubedl_download(video_url)
