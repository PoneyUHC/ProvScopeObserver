#!/bin/bash

SCRIPT_DIR="$(dirname "$0")"
source ${SCRIPT_DIR}/common.bash

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

ssh -t $DIST_VM_USER@$DIST_VM_ADDR "rm -rf ~/${PROJECT_NAME} && mkdir -p ~/${PROJECT_NAME}/"
scp -r ~/ProvScopeObserver/* $DIST_VM_USER@$DIST_VM_ADDR:~/${PROJECT_NAME}

ssh -t $DIST_VM_USER@$DIST_VM_ADDR "cd ~/${PROJECT_NAME} && python3 -m venv venv && source ./venv/bin/activate && pip install -e . && ~/${PROJECT_NAME}/${SCRIPTS_DIR}/run.bash ${n_exec} ${wait_time}"

scp -r $DIST_VM_USER@$DIST_VM_ADDR:~/${PROJECT_NAME}/${RESULTS_DIR}/output/ ${RESULTS_DIR}/output/