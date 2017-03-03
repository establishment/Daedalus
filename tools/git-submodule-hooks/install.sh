#!/bin/bash
location=$(git rev-parse --git-dir)
echo "\
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Copy git-hooks so git pull/checkout
triggers git submodule update and 
if it can checkout the targeted branch
without changing the head sha, it does
it. 
.git folder location
$location
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"

cp -r ./hooks $location
