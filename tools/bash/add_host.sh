#!/usr/bin/env bash

sed -i "/$1.*/d" /etc/hosts
sed -i "/.*$2/d" /etc/hosts
echo "$1     $2" >> /etc/hosts
