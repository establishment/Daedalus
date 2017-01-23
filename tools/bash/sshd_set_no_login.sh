#!/usr/bin/env bash

sed -i "/PermitRootLogin.*/d" /etc/ssh/sshd_config
echo "PermitRootLogin without-password" >> /etc/ssh/sshd_config

/etc/init.d/sshd restart
