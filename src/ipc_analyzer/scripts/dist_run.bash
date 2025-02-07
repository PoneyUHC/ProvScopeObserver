#!/bin/bash

source ./scripts/config.bash

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

# ssh -t $DIST_VM_USER@$DIST_VM_ADDR "rmdir ~/${PROJECT_NAME}"
scp -r evaluator_interface/ present_result/ ${PROGRAMS_DIR} ${SCRIPTS_DIR} trace/ $DIST_VM_USER@$DIST_VM_ADDR:~/${PROJECT_NAME}
ssh -t $DIST_VM_USER@$DIST_VM_ADDR "cd  ~/${PROJECT_NAME} && ~/${PROJECT_NAME}/${SCRIPTS_DIR}/run.bash ${n_exec} ${wait_time}"

scp -r $DIST_VM_USER@$DIST_VM_ADDR:~/${PROJECT_NAME}/present_result/output/ present_result/output/