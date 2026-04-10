#!/bin/bash

SCRIPT_DIR="$(dirname "$0")"

n_exec=1
report_filename=report
wait_time=1000
evaluator_actions_script=none
system_executable=none
monitor_version=bpftrace024
system_executable_args=none
if [ $# -lt 7 ]
    then
        echo "Usage : $0 [n_exec] [report_filename] [wait_time] [evaluator_actions_script] [processes] [monitor_version] [system_executable] [system_executable_args...]"
        exit 1
    else
        n_exec=$1
        report_filename=$2
        wait_time=$3
        evaluator_actions_script=$4
        processes=$5
        monitor_version=$6
        system_executable=$7
        system_executable_args=${@:8}
fi

for ((i = 0 ; i < $n_exec ; i++ ));
do
    source ${SCRIPT_DIR}/exec.bash ${report_filename}_${i}.json ${wait_time} ${evaluator_actions_script} ${processes} ${monitor_version} ${system_executable} ${system_executable_args}; 
done
