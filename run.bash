#! /bin/bash

export BPFTRACE_MAX_STRLEN=90

CLOSE_STDIN=< /dev/null

ARGS=$$
PROGRAMS_DIR=programs
BINARIES_DIR=$PROGRAMS_DIR/build/exec
BPF_SCRIPTS_DIR=trace
BPF_LOGS_DIR=trace/logs

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

make -C $PROGRAMS_DIR

# get the sudo confirmation before the ones backgrounding
sudo true
# sudo bpftrace --unsafe trace/trace_all_user_functions.bt $(realpath .)/programs/build/exec/router.bin -o trace/logs/trace_all_user_functions.logs&
sudo bpftrace $BPF_SCRIPTS_DIR/trace_open.bt $ARGS $CLOSE_STDIN > $BPF_LOGS_DIR/trace_open.logs &
sudo bpftrace $BPF_SCRIPTS_DIR/trace_close.bt $ARGS $CLOSE_STDIN > $BPF_LOGS_DIR/trace_close.logs &
sudo bpftrace $BPF_SCRIPTS_DIR/trace_write.bt $ARGS $CLOSE_STDIN > $BPF_LOGS_DIR/trace_write.logs $CLOSE_STDIO &
sudo bpftrace $BPF_SCRIPTS_DIR/trace_read.bt $ARGS $CLOSE_STDIN > $BPF_LOGS_DIR/trace_read.logs $CLOSE_STDIO &

sleep 2

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
python3 present_result/export_result.py