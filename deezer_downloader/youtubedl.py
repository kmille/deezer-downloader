import re
from shlex import quote
from subprocess import Popen, PIPE

from deezer_downloader.configuration import config


class YoutubeDLFailedException(Exception):
    pass


class DownloadedFileNotFoundException(Exception):
    pass


def execute(cmd):
    print('Executing "{}"'.format(cmd))
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    p.wait()
    stdout, stderr = p.communicate()
    print(stdout.decode())
    if p.returncode != 0:
        print(stderr.decode())
        raise YoutubeDLFailedException("ERROR: youtube-dl exited with non-zero: \n{}\nYou may have to update it!".format(stderr.decode()))
    return get_absolute_filename(stdout.decode(), stderr.decode())


def get_absolute_filename(stdout, stderr):
    regex_foo = re.search(r'Destination:\s(.*mp3)', stdout)
    if not regex_foo:
        raise DownloadedFileNotFoundException("ERROR: Can not extract output file via regex. \nstderr: {}\nstdout: {}".format(stderr, stdout))
    return regex_foo.group(1)


def youtubedl_download(url, destination_dir, proxy=None):
    # url, e.g. https://www.youtube.com/watch?v=ZbZSe6N_BXs
    # destination_dir: /tmp/
    # proxy: https/socks5 proxy (e. g. socks5://user:pass@127.0.0.1:1080/)
    # returns: absolute filename of the downloaded file
    # raises
    # YoutubeDLFailedException if youtube-dl exits with non-zero
    # DownloadedFileNotFoundException if we cannot get the converted output file from youtube-dl with a regex

    proxy_command = f" --proxy {proxy}" if proxy else ""
    youtube_dl_cmd = config["youtubedl"]["command"] + \
        proxy_command + \
        " -x --audio-format mp3 " + \
        "--audio-quality 0 " + \
        f"-o '{destination_dir}/%(title)s.%(ext)s' " + \
        "--embed-metadata " + \
        "--no-embed-chapters " + \
        quote(url)

    filename_absolute = execute(youtube_dl_cmd)
    return filename_absolute


if __name__ == '__main__':
    video_url = "https://www.invidio.us/watch?v=ZbZSe6N_BXs"
    youtubedl_download(video_url, "/tmp/music/deezer/youtube-dl")
