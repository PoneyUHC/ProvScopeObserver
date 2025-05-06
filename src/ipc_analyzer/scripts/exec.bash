#!/bin/bash


SCRIPT_DIR="$(dirname "$0")"
source ${SCRIPT_DIR}/common.bash

if [ $# -lt 3 ]
    then
        echo "Usage : $0 [report_filename] [wait_time] [n_clients]"
        exit 1
fi

REPORT_FILENAME=$1
WAIT_TIME=$2
N_CLIENTS=$3
TALK_DELAY=$4
ARGS=$$

[ ! -d $BPF_LOGS_DIR ] && mkdir -p $BPF_LOGS_DIR

already_cleaned=0

cleanup() {
    if [ $already_cleaned -eq 1 ]; then
        return
    fi
    kill $(jobs -p)
    pgrep bpftrace | xargs sudo kill -9
    already_cleaned=1
}

trap 'cleanup' EXIT

sudo true

python3 ${BPF_SCRIPTS_DIR}/trace.py ${ARGS} &

sleep 1

python3 ${PROGRAMS_DIR}/run.py ${N_CLIENTS} ${TALK_DELAY} &

sleep 2

python3 ${SRC_DIR}/evaluator_interface/auto_attacker.py ${SRC_DIR}/evaluator_interface/scenario.json

echo "Finished interaction, keeping running for ${WAIT_TIME} more seconds"
echo "Ctrl+C this process when you would like to stop the monitoring..."
sleep ${WAIT_TIME}

cleanup

# create report from logs
echo "Exporting results to file ${REPORT_FILENAME}" 
python3 ${SRC_DIR}/present_result/export_result.py ${REPORT_FILENAME}
