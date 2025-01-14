#!/bin/bash

source ./scripts/config.bash

n_exec=1
if [ $# -ge 1 ]
    n_exec= $1
fi

scp -r evaluator_interface/ present_result/ ${PROGRAMS_DIR} ${SCRIPTS_DIR} trace/ $DIST_VM_USER@$DIST_VM_ADDR:~/${PROJECT_NAME}
ssh -t $DIST_VM_USER@$DIST_VM_ADDR "cd  ~/${PROJECT_NAME} && ~/${PROJECT_NAME}/${SCRIPTS_DIR}/run.bash ${n_exec}"

scp $DIST_VM_USER@$DIST_VM_ADDR:~/${PROJECT_NAME}/present_result/output/* present_result/output/*