#! /bin/bash

source ./scripts/config.bash

scp -r evaluator_interface/ present_result/ ${PROGRAMS_DIR} ${SCRIPTS_DIR} trace/ $DIST_VM_USER@$DIST_VM_ADDR:~/${PROJECT_NAME}
ssh -t $DIST_VM_USER@$DIST_VM_ADDR "cd  ~/${PROJECT_NAME} && ~/${PROJECT_NAME}/${SCRIPTS_DIR}/run.bash"

scp $DIST_VM_USER@$DIST_VM_ADDR:~/${PROJECT_NAME}/present_result/output/model.json present_result/output/model.json