#!/usr/bin/env bash

apt-get install -y git

cd /
mkdir -p tools
cd tools
git clone https://github.com/establishment/Daedalus
cd Daedalus

. install.sh
