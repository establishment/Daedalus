#!/usr/bin/env bash

DIRECTORY=$1

cwd=$(pwd)
cd $DIRECTORY

$2 "${@:3}"

cd ${cwd}
