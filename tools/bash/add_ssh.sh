#!/usr/bin/env bash

NAME=$1

eval "$(ssh-agent -s)"
ssh-add ~/.ssh/$NAME
