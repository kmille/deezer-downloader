# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "debian/buster64"
  config.vm.box_check_update = false

  config.vm.network "forwarded_port", guest: 5000, host: 5000, host_ip: "127.0.0.1"
  config.vm.network "forwarded_port", guest: 6600, host: 6600, host_ip: "127.0.0.1"

   config.vm.provider "virtualbox" do |vb|
     vb.gui = false
     vb.memory = "512"
   end
  
   config.vm.provision "shell", inline: <<-SHELL
      apt-get update -q
      apt-get install -qy vim tmux git gcc
      apt-get install -qy python3-virtualenv python3-dev
      git clone https://github.com/kmille/deezer-downloader.git /opt/deezer
      python3 -m virtualenv -p python3 /opt/deezer/app/venv
      source /opt/deezer/app/venv/bin/activate && pip install -r /opt/deezer/requirements.txt && deactivate
      source /opt/deezer/app/venv/bin/activate && pip install -U youtube-dl && deactivate
      cp /opt/deezer/app/settings.ini.example /opt/deezer/app/settings.ini
      sed -i 's/.*use_mpd = False.*/use_mpd = True/' /opt/deezer/app/settings.ini
      sed -i 's/.*host = 127.0.0.1.*/host = 0.0.0.0/' /opt/deezer/app/settings.ini
      sed -i 's,.*command = /usr/bin/youtube-dl.*,command = /opt/deezer/app/venv/bin/youtube-dl,' /opt/deezer/app/settings.ini
      apt-get install -yq mpd ncmpcpp
      sed -i 's/^bind_to_address.*"localhost"/bind_to_address         "0.0.0.0"/' /etc/mpd.conf
      sed -i 's,^music_directory.*,music_directory         "/tmp/deezer-downloader",' /etc/mpd.conf
      systemctl restart mpd
      echo "1) Adjust the Deezer Cookie in /opt/deezer/app/settings.ini" >> /etc/motd
      echo "2) Run it: /opt/deezer/app/venv/bin/python /opt/deezer/app/app.py" >> /etc/motd
      echo "3) Try out: ncmpcpp -h 127.0.0.1 (you won't hear anything. Use it on a Rasberry Pi!" >> /etc/motd
   SHELL
end
