#!/bin/bash

SCRIPT_DIR="$(dirname "$0")"

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
<<<<<<< HEAD:scripts/run.bash
    ./scripts/build.bash
    ./scripts/exec.bash report${printf "%02d" $i}.json ${wait_time};
=======
    source ${SCRIPT_DIR}/build.bash
    source ${SCRIPT_DIR}/exec.bash report${i}.json ${wait_time}; 
>>>>>>> 3e385ac (bash to python transition wip):src/ipc_analyzer/scripts/run.bash
done