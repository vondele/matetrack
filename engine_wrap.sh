#!/bin/sh

eval "$@" | grep --line-buffered -v bound
