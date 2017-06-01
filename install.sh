#!/usr/bin/env bash

# you have to run this as: ". install.sh" or restart current shell session/reload bashrc file

#MY_PATH="`dirname \"$0\"`"              # relative
#MY_PATH="`( cd \"$MY_PATH\" && pwd )`"  # absolutized and normalized
#if [ -z "$MY_PATH" ] ; then
#  # error; for some reason, the path is not accessible
#  # to the script (e.g. permissions re-evaled after suid)
#  exit 1  # fail
#fi

#cd $MY_PATH

apt-get update
apt-get install -y curl
apt-get install -y python3
apt-get install -y python3-setuptools
apt-get install -y python3-dev
apt-get install -y python3-pip
easy_install3 pip
pip install --upgrade pip
curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python
curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python3
pip3 install Jinja2
pip3 install colorama

python3 source/daedalus.py install

. /etc/profile
. /etc/bash.bashrc
. ~/.bash_profile
. ~/.bash_login
. ~/.profile
