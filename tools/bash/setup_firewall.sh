#!/bin/bash

#This script must be executed on the target server as root.

# Install iptables-persistent
echo iptables-persistent iptables-persistent/autosave_v4 boolean true | sudo debconf-set-selections
echo iptables-persistent iptables-persistent/autosave_v6 boolean true | sudo debconf-set-selections
sudo apt-get install -y iptables-persistent

#Configure iptables service to automatically start on reboot
chkconfig --level 235 iptables on

# Flush all current rules from iptables
iptables -F

# GROUND RULES: Allow established TCP traffic
iptables -A INPUT -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A OUTPUT -m state --state NEW,RELATED,ESTABLISHED -j ACCEPT

# ALLOW: ssh, smtp, http, https, pings, local traffic
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -p tcp --dport 25 -j ACCEPT
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -p icmp -j ACCEPT
iptables -A INPUT -s 127.0.0.1 -j ACCEPT

# DROP: Force SYN packets check
iptables -A INPUT -p tcp ! --syn -m state --state NEW -j DROP

# DROP: packets with incoming fragments
iptables -A INPUT -f -j DROP

# DROP: incoming malformed XMAS packets
iptables -A INPUT -p tcp --tcp-flags ALL ALL -j DROP

# DROP: incoming malformed NULL packets
iptables -A INPUT -p tcp --tcp-flags ALL NONE -j DROP

# REJECT: anything that wasn't explicitly allowed
iptables -A INPUT -j REJECT
iptables -A FORWARD -j REJECT

# Save rules so they'll be used after reboots
iptables-save > /etc/iptables/rules.v4
ip6tables-save > /etc/iptables/rules.v6

# iptables-restore < /etc/iptables/rules.v4
# ip6tables-restore < /etc/iptables/rules.v6