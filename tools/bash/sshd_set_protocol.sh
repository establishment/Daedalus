#!/usr/bin/env bash

sed -i "/Protocol.*/d" /etc/ssh/sshd_config
echo "Protocol $1" >> /etc/ssh/sshd_config

/etc/init.d/sshd restart
