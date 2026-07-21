#!/bin/bash

PROJECT_NAME=provscope_observer

CLOSE_STDIN= 0<&-

SRC_DIR="$(dirname "$(dirname "$0")")"

SCRIPTS_DIR=${SRC_DIR}/scripts
RESULTS_DIR=${SRC_DIR}/trace_export

BPF_SCRIPTS_DIR=${SRC_DIR}/tracers
BPF_LOGS_DIR=${BPF_SCRIPTS_DIR}/run/logs
