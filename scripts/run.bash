#!/bin/bash

./scripts/build.bash

n_exec=1
wait_time=1000
if [ $# -lt 1 ]
    then
        echo "Usage : $0 [n_exec] [wait_time]"
        exit 1
    else
        n_exec=$1
        wait_time=$2
fi

for ((i = 0 ; i < $n_exec ; i++ ));
do
    ./scripts/build.bash
    ./scripts/exec.bash report${i}.json ${wait_time}; 
done