#!/usr/bin/env bash

RETURN_STRING=""

tolower()
{
	echo $1 | tr "[:upper:]" "[:lower:]" ;
}

toupper()
{
	echo $1 | tr "[:lower:]" "[:upper:]" ;
}

function ensure_dot_path {
    if [[ $1 == /* ]] ; then
        echo $1
    else
        echo ./$1
    fi
}

function fextract {
    local path=$(ensure_dot_path $1)
    if [ -z "$path" ]; then
        # display usage if no parameters given
        echo "Usage: extract <path/file_name>.<zip|rar|bz2|gz|tar|tbz2|tgz|Z|7z|xz|ex|tar.bz2|tar.gz|tar.xz>"
    else
        if [ -f "$path" ] ; then
            local nameInLowerCase=`echo "$path" | awk '{print tolower($0)}'`
            case "$nameInLowerCase" in
                *.tar.bz2)   file=$(echo -n ${path} | head -c -8)
                             rm -rf ${file} >/dev/null 2>&1
                             tar xvjf ${path} >/dev/null 2>&1
                             echo ${file};;
                *.tar.gz)    file=$(echo -n $1 | head -c -7)
                             rm -rf ${file} >/dev/null 2>&1
                             tar xvzf ${path} >/dev/null 2>&1
                             echo ${file};;
                *.tar.xz)    file=$(echo -n $1 | head -c -7)
                             rm -rf ${file} >/dev/null 2>&1
                             tar xvJf ${path} >/dev/null 2>&1
                             echo ${file};;
                *.lzma)      file=$(echo -n $1 | head -c -5)
                             rm -rf ${file} >/dev/null 2>&1
                             unlzma ${path} >/dev/null 2>&1
                             echo ${file};;
                *.bz2)       file=$(echo -n $1 | head -c -4)
                             rm -rf ${file} >/dev/null 2>&1
                             bunzip2 ${path} >/dev/null 2>&1
                             echo ${file};;
                *.rar)       file=$(echo -n $1 | head -c -4)
                             rm -rf ${file} >/dev/null 2>&1
                             unrar x -ad ${path} >/dev/null 2>&1
                             echo ${file};;
                *.gz)        file=$(echo -n $1 | head -c -3)
                             rm -rf ${file} >/dev/null 2>&1
                             gunzip ${path} >/dev/null 2>&1
                             echo ${file};;
                *.tar)       file=$(echo -n $1 | head -c -4)
                             rm -rf ${file} >/dev/null 2>&1
                             tar xvf ${path} >/dev/null 2>&1
                             echo ${file};;
                *.tbz2)      file=$(echo -n $1 | head -c -5)
                             rm -rf ${file} >/dev/null 2>&1
                             tar xvjf ${path} >/dev/null 2>&1
                             echo ${file};;
                *.tgz)       file=$(echo -n $1 | head -c -4)
                             rm -rf ${file} >/dev/null 2>&1
                             tar xvzf ${path}
                             echo ${file};;
                *.zip)       file=$(echo -n $1 | head -c -4)
                             rm -rf ${file} >/dev/nul 2>&1
                             unzip ${path} >/dev/null 2>&1
                             echo ${file};;
                *.Z)         file=$(echo -n $1 | head -c -2)
                             rm -rf ${file} >/dev/null 2>&1
                             uncompress ${path} >/dev/null 2>&1
                             echo ${file};;
                *.7z)        file=$(echo -n $1 | head -c -3)
                             rm -rf ${file} >/dev/null 2>&1
                             7z x ${path} >/dev/null 2>&1
                             echo ${file};;
                *.xz)        file=$(echo -n $1 | head -c -3)
                             rm -rf ${file} >/dev/null 2>&1
                             unxz ${path} >/dev/null 2>&1
                             echo ${file};;
                *.exe)       file=$(echo -n $1 | head -c -4)
                             rm -rf ${file} >/dev/null 2>&1
                             cabextract ${path} >/dev/null 2>&1
                             echo ${file};;
                *)           echo $path ;;
            esac
            else
                echo "fextract: '${path}' - file does not exist"
        fi
    fi
}

function extract {
    local path=$(ensure_dot_path $1)
    if [ -z "$path" ]; then
        # display usage if no parameters given
        echo "Usage: extract <path/file_name>.<zip|rar|bz2|gz|tar|tbz2|tgz|Z|7z|xz|ex|tar.bz2|tar.gz|tar.xz>"
    else
        if [ -f "$path" ] ; then
            local nameInLowerCase=`echo "${path}" | awk '{print tolower($0)}'`
            case "$nameInLowerCase" in
                *.tar.bz2)   tar xvjf ${path}    ;;
                *.tar.gz)    tar xvzf ${path}    ;;
                *.tar.xz)    tar xvJf ${path}    ;;
                *.lzma)      unlzma ${path}      ;;
                *.bz2)       bunzip2 ${path}     ;;
                *.rar)       unrar x -ad ${path} ;;
                *.gz)        gunzip ${path}      ;;
                *.tar)       tar xvf ${path}     ;;
                *.tbz2)      tar xvjf ${path}    ;;
                *.tgz)       tar xvzf ${path}    ;;
                *.zip)       unzip ${path}       ;;
                *.Z)         uncompress ${path}  ;;
                *.7z)        7z x ${path}        ;;
                *.xz)        unxz ${path}        ;;
                *.exe)       cabextract ${path}  ;;
                *)           echo "extract: '${path}' - unknown archive method" ;;
            esac
        else
            echo "extract: '$path' - file does not exist"
        fi
    fi
}

function escape_slashes {
    sed 's/\//\\\//g'
}

function change_line {
    local OLD_LINE_PATTERN=$1; shift
    local NEW_LINE=$1; shift
    local FILE=$1

    local NEW=$(echo "${NEW_LINE}" | escape_slashes)
    sed -i .bak '/'"${OLD_LINE_PATTERN}"'/s/.*/'"${NEW}"'/' "${FILE}"
    mv "${FILE}.bak" /tmp/
}

function myreadlink() {
    (
    cd $(dirname $1)         # or  cd ${1%/*}
    echo $PWD/$(basename $1) | sed -r "s/\/\//\//g"   # or  echo $PWD/${1##*/}
    )
}
