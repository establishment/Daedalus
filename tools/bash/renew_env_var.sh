#!/usr/bin/env bash

sed -i "/export $1=.*/d" /etc/profile
export $1=$2
echo "export $1=$2" >> /etc/profile