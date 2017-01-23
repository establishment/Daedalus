#!/bin/bash
#
# send gratuitous arp out for each ip on this machine (inet/inet6 tay appention)
#
for ip in `/sbin/ip a |grep -w inet|awk '{print $2 " " $NF}'|sed -e 's/:[0-9]\+//g' -e 's/\/[0-9]\+ /,/g'`
do
  nic=$(echo ${ip}|awk -F, '{print $2}')
  addr=$(echo ${ip}|awk -F, '{print $1}')
  echo "[INFO] - running gratuitous arp of ${addr} on ${nic}"
  /usr/sbin/arping -i ${nic} -d -S ${addr} -B -c 5
done
