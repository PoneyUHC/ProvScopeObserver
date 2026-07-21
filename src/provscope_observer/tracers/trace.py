
import os
import time

import subprocess

from provscope_observer.utils import EndProcessWatcher

ERR_BAD_ARG = 1


def start():

    procs = []

    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)
    if os.path.exists('run/logs') is False:
        os.makedirs('run/logs')

    with open('run/logs/trace_open.logs', 'w') as fout:
        with open('run/logs/trace_open.err', 'w') as ferr:
            p = subprocess.Popen(['sudo', 'bpftrace', '-f', 'json', 'run/scripts/trace_open.bt', '-o', fout.name], stderr=ferr, stdout=ferr)
            procs.append(p)

    with open('run/logs/trace_close.logs', 'w') as fout:
        with open('run/logs/trace_close.err', 'w') as ferr:
            p = subprocess.Popen(['sudo', 'bpftrace', '-f', 'json', 'run/scripts/trace_close.bt', '-o', fout.name], stderr=ferr, stdout=ferr)
            procs.append(p)

    with open('run/logs/trace_write.logs', 'w') as fout:
        with open('run/logs/trace_write.err', 'w') as ferr:
            p = subprocess.Popen(['sudo', 'bpftrace', '-f', 'json', 'run/scripts/trace_write.bt', '-o', fout.name], stderr=ferr, stdout=ferr)
            procs.append(p)

    with open('run/logs/trace_read.logs', 'w') as fout:
        with open('run/logs/trace_read.err', 'w') as ferr:
            p = subprocess.Popen(['sudo', 'bpftrace', '-f', 'json', 'run/scripts/trace_read.bt', '-o', fout.name], stderr=ferr, stdout=ferr)
            procs.append(p)

    return procs



def clean(procs: list[subprocess.Popen]):

    for p in procs:
        subprocess.run(['sudo', 'kill', '-INT', f"{p.pid}"])


def main():

    watcher = EndProcessWatcher()

    procs = start()
    
    while not watcher.kill_now:
        time.sleep(0.2)

    clean(procs)


main()