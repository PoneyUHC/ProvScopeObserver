#! /bin/bash

export BPFTRACE_MAX_STRLEN=90

ARGS=$$
PROGRAMS_DIR=programs
BINARIES_DIR=$PROGRAMS_DIR/build/exec
BPF_SCRIPTS_DIR=trace
BPF_LOGS_DIR=trace/logs

[ ! -d $BPF_LOGS_DIR ] && mkdir -p $BPF_LOGS_DIR

trap 'kill $(jobs -p)' EXIT

make -C $PROGRAMS_DIR

bpftrace --unsafe trace/trace_all_user_functions.bt /home/loic/OneDrive/phd_shared/phd/IPC_Analyzer/programs/build/exec/router.bin -o trace/logs/trace_all_user_functions.logs&
bpftrace $BPF_SCRIPTS_DIR/trace_open.bt $ARGS -o $BPF_LOGS_DIR/trace_open.logs&
#bpftrace $BPF_SCRIPTS_DIR/trace_write.bt $ARGS -o $BPF_LOGS_DIR/trace_write.logs&
#bpftrace $BPF_SCRIPTS_DIR/trace_read.bt $ARGS -o $BPF_LOGS_DIR/trace_read.logs&
#sleep 2


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
./attacker.bin run/att_r run/att_l
