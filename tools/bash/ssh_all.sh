#!/bin/bash

# this script will ssh into all hostnames/IPs
# passed to it and run whichever command specified

# print some usage text if no arguments are given
[[ -n "$1" ]] || { echo "Usage: ssh_all \"command\" [server_list.txt] OR [server1 server2 server3] ..."; exit 0 ; }

# pull the first arg out since that is going to be our command sent to ssh
COMMAND=$1
shift

# if next arg is a file, then use that as the list of servers
# otherwise use the remaining args as your server list
if [ -f $1 ]; then
     SERVER_LIST=$(cat $1)
else
     SERVER_LIST=$@
fi

# specify some options
# use option -oStrictHostKeyChecking=no to get rid of that annoying RSA warning.
SSH_OPTIONS="-oStrictHostKeyChecking=no"

# do it!
for SERVER in $SERVER_LIST; do
     echo ""
     echo "Running '$COMMAND' on $SERVER"
     echo $COMMAND | ssh $SSH_OPTIONS $SERVER /bin/bash
     echo "----------------------"
done
