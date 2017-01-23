#!/usr/bin/env bash

sed -i "/Port.*/d" /etc/ssh/sshd_config
echo "Port $1" >> /etc/ssh/sshd_config

/etc/init.d/sshd restart
