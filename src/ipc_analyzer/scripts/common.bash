#!/bin/bash

PROJECT_NAME=ipc_analyzer

BPFTRACE_MAX_STRLEN=90

CLOSE_STDIN= 0<&-

SRC_DIR="$(dirname "$(dirname "$0")")"

PROGRAMS_DIR=${SRC_DIR}/programs
SCRIPTS_DIR=${SRC_DIR}/scripts

BINARIES_DIR=$PROGRAMS_DIR/build/exec

BPF_SCRIPTS_DIR=${SRC_DIR}/trace
BPF_LOGS_DIR=${BPF_SCRIPTS_DIR}/logs
