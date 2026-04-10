#!/bin/bash


SCRIPT_DIR="$(dirname "$0")"
source ${SCRIPT_DIR}/common.bash

if [ $# -lt 6 ]
    then
        echo "Usage : $0 [report_filename] [wait_time] [evaluator_actions_script] [processes] [monitor_version] [system_executable] [system_executable_args...]"
        exit 1
fi

REPORT_FILENAME=$1
WAIT_TIME=$2
EVALUATOR_ACTIONS_SCRIPT=$3
PROCESSES=$4
MONITOR_VERSION=$5
SYSTEM_EXECUTABLE=$6
SYSTEM_EXECUTABLE_ARGS=${@:7} # system executable arguments

BPF_RUN_DIR=${BPF_SCRIPTS_DIR}/run/${MONITOR_VERSION}
BPF_LOGS_DIR=${BPF_RUN_DIR}/logs

[ ! -d $BPF_LOGS_DIR ] && mkdir -p $BPF_LOGS_DIR

already_cleaned=0

cleanup() {
    if [ $already_cleaned -eq 1 ]; then
        return
    fi
    kill $(jobs -p)
    pgrep bpftrace | xargs sudo kill -INT
    already_cleaned=1
}

trap 'cleanup' EXIT

python3 ${BPF_SCRIPTS_DIR}/instantiate_templates.py ${MONITOR_VERSION} ${PROCESSES}

sudo true

python3 ${BPF_SCRIPTS_DIR}/trace.py ${MONITOR_VERSION} &

sleep 3

python3 ${SYSTEM_EXECUTABLE} ${SYSTEM_EXECUTABLE_ARGS} &

sleep 2

${EVALUATOR_ACTIONS_SCRIPT}

echo "Finished interaction, keeping running for ${WAIT_TIME} more seconds"
echo "Ctrl+C this process when you would like to stop the monitoring..."
sleep ${WAIT_TIME}

cleanup

# wait for bpftrace processes to terminate and flush logs
sleep 2

for f in "${BPF_LOGS_DIR}"/*; do
    [ -f "$f" ] || continue
    if sed '1d' "$f" | jq . > "${f}.jqtmp" 2>/dev/null; then
        mv "${f}.jqtmp" "$f"
    else
        echo "Warning: jq failed for $f, skipping" >&2
        rm -f "${f}.jqtmp"
    fi
done

echo "Processing logs..."
sleep 2

# create report from logs
echo "Exporting results to file ${REPORT_FILENAME}" 
python3 ${SRC_DIR}/present_result/export_result.py ${MONITOR_VERSION} ${REPORT_FILENAME}
