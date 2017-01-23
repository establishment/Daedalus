#!/usr/bin/env bash

# you have to run this as: ". install.sh" or restart current shell session/reload bashrc file

apt-get install -y python3
apt-get install -y python3-setuptools
apt-get install -y python3-dev
easy_install3 pip
pip install Jinja2

python3 source/daedalus.py install

. /etc/profile
. /etc/bash.bashrc
. ~/.bash_profile
. ~/.bash_login
. ~/.profile
