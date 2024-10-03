#! /bin/bash

make
cd build/exec/

trap 'kill $(jobs -p)' EXIT

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
