#!/bin/bash

PROJECT_NAME=ipc_analyzer

CLOSE_STDIN= 0<&-

SRC_DIR="$(dirname "$(dirname "$0")")"

PROGRAMS_DIR=${SRC_DIR}/programs
SCRIPTS_DIR=${SRC_DIR}/scripts
RESULTS_DIR=${SRC_DIR}/present_result

BINARIES_DIR=${PROGRAMS_DIR}/build/exec

BPF_SCRIPTS_DIR=${SRC_DIR}/trace
