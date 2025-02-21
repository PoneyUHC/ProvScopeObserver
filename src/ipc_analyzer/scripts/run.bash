#!/bin/bash

SCRIPT_DIR="$(dirname "$0")"

n_exec=1
wait_time=1000
if [ $# -lt 3 ]
    then
        echo "Usage : $0 [n_exec] [wait_time] [n_clients]"
        exit 1
    else
        n_exec=$1
        wait_time=$2
        n_clients=$3
fi

for ((i = 0 ; i < $n_exec ; i++ ));
do
    source ${SCRIPT_DIR}/exec.bash report${i}.json ${wait_time} ${n_clients}; 
done