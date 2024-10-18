#! /bin/bash

trap 'kill $(jobs -p)' EXIT

make

bpftrace ./trace_enter_open.bt -o trace_enter_open.logs&
bpftrace ./trace_write.bt -o trace_write.logs&
bpftrace ./trace_read.bt -o trace_read.logs&
sleep 0.5

cd build/exec/
# order matters for fifo openings
./target.bin run/r_a1 > run/a1.logs&
sleep 0.1
./target.bin run/r_a2 > run/a2.logs&
sleep 0.1
./log_collector.bin run/att_l run/logs run/goal > run/log_c.logs&
sleep 0.1
./router.bin run/att_r run/r_a1 run/r_a2 run/logs > run/router.logs&
sleep 0.1
./attacker.bin run/att_r run/att_l
