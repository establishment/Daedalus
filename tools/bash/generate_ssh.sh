#!/usr/bin/env bash

NAME=$1
LABEL=$2

ssh-keygen -t rsa -b 4096 -C "$LABEL" -P "" -f ~/.ssh/$NAME
