
import sys
import os
import time

import subprocess

from ipc_analyzer.utils import EndProcessWatcher

ERR_BAD_ARG = 1


def start():

    procs = []

    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)

    with open('logs/trace_open.logs', 'w') as fout:
        p = subprocess.Popen(['sudo', 'bpftrace', 'trace_open.bt', sys.argv[1]], stdout=fout)
        procs.append(p)

    with open('logs/trace_close.logs', 'w') as fout:
        p = subprocess.Popen(['sudo', 'bpftrace', 'trace_close.bt', sys.argv[1]], stdout=fout)
        procs.append(p)

    with open('logs/trace_write.logs', 'w') as fout:
        p = subprocess.Popen(['sudo', 'bpftrace', 'trace_write.bt', sys.argv[1]], stdout=fout)
        procs.append(p)

    with open('logs/trace_read.logs', 'w') as fout:
        p = subprocess.Popen(['sudo', 'bpftrace', 'trace_read.bt', sys.argv[1]], stdout=fout)
        procs.append(p)

    return procs



def clean(procs: list[subprocess.Popen]):

    for p in procs:
        subprocess.run(['sudo', 'kill', f"{p.pid}"])


def main():

    if len(sys.argv) != 2:
        print("Usage: trace.py <arg>")
        sys.exit(ERR_BAD_ARG)

    watcher = EndProcessWatcher()

    procs = start()
    
    while not watcher.kill_now:
        time.sleep(1)

    clean(procs)


main()