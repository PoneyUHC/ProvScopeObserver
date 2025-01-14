#!/bin/bash

./scripts/build.bash

n_exec=1
if [ $# -eq 0 ]
    then
        echo "No arguments supplied, executing only once"
    else
        n_exec=$1
fi

./scripts/exec.bash $n_exec