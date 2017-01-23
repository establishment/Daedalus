#!/usr/bin/env bash

hostnamectl set-hostname $1

echo $1 > /etc/hostname
${DAEDALUS_ROOT}/tools/bash/add_host.sh "127.0.1.1" $1

hostname $1
