#!/bin/bash

stat=`status ssh`
echo $stat
#stat is returned like: ssh start/running, process 1602
goal=`echo $stat|cut -f2 -d" "|cut -f1 -d/`
#cut the 2nd field afetr 1st space; then cut the 1st field before "/" to get the "goal" of the ssh job.

#ignoring the status
echo $goal
if [ "$goal" == "start" ];
then
  service ssh stop
else
  service ssh start
fi
