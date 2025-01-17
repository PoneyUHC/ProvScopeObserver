#!/bin/bash

if [ $# -lt 2 ]
    then
        echo "Usage : $0 [report_filename] [wait_time]"
        exit 1
fi

REPORT_FILENAME=$1
WAIT_TIME=$2

source ./scripts/config.bash

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

# get the sudo confirmation before the ones backgrounding
sudo true
# sudo bpftrace --unsafe trace/trace_all_user_functions.bt $(realpath .)/programs/build/exec/router.bin -o trace/logs/trace_all_user_functions.logs&
sudo bpftrace $BPF_SCRIPTS_DIR/trace_open.bt $ARGS $CLOSE_STDIN > $BPF_LOGS_DIR/trace_open.logs &
sudo bpftrace $BPF_SCRIPTS_DIR/trace_close.bt $ARGS $CLOSE_STDIN > $BPF_LOGS_DIR/trace_close.logs &
sudo bpftrace $BPF_SCRIPTS_DIR/trace_write.bt $ARGS $CLOSE_STDIN > $BPF_LOGS_DIR/trace_write.logs $CLOSE_STDIO &
sudo bpftrace $BPF_SCRIPTS_DIR/trace_read.bt $ARGS $CLOSE_STDIN > $BPF_LOGS_DIR/trace_read.logs $CLOSE_STDIO &

sleep 1

cd $BINARIES_DIR
# order matters for fifo openings
./target.bin run/r_a1 > run/a1.logs&
sleep 0.5
./target.bin run/r_a2 > run/a2.logs&
sleep 0.5
./log_collector.bin run/att_l run/logs run/goal > run/log_c.logs&
sleep 0.5
./router.bin run/att_r run/r_a1 run/r_a2 run/logs > run/router.logs&
sleep 0.5


cd -
python3 evaluator_interface/auto_attacker.py evaluator_interface/scenario.json

cleanup

# create report from logs
python3 present_result/export_result.py $REPORT_FILENAME

echo "Finished interaction, keeping running for $WAIT_TIME more seconds"
echo "Ctrl+C this process when you would like to stop the monitoring..."
sleep $WAIT_TIME