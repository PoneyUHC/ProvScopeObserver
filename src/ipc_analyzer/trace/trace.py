
import os
import time

import subprocess

from ipc_analyzer.utils import EndProcessWatcher

ERR_BAD_ARG = 1


def start():

    procs = []

    env = os.environ.copy()
    env["BPFTRACE_MAX_STRLEN"] = "150"

    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)
    if os.path.exists('run/logs') is False:
        os.makedirs('run/logs')

    with open('run/logs/trace_open.logs', 'w') as fout:
        p = subprocess.Popen(['sudo', '-E', 'bpftrace', '-f', 'json', 'run/scripts/trace_open.bt'], stdout=fout, env=env)
        procs.append(p)

    with open('run/logs/trace_close.logs', 'w') as fout:
        p = subprocess.Popen(['sudo', '-E', 'bpftrace', '-f', 'json', 'run/scripts/trace_close.bt'], stdout=fout, env=env)
        procs.append(p)

    with open('run/logs/trace_write.logs', 'w') as fout:
        p = subprocess.Popen(['sudo', '-E', 'bpftrace', '-f', 'json', 'run/scripts/trace_write.bt'], stdout=fout, env=env)
        procs.append(p)

    with open('run/logs/trace_read.logs', 'w') as fout:
        p = subprocess.Popen(['sudo', '-E', 'bpftrace', '-f', 'json', 'run/scripts/trace_read.bt'], stdout=fout, env=env)
        procs.append(p)

    return procs



def clean(procs: list[subprocess.Popen]):

    for p in procs:
        subprocess.run(['sudo', 'kill', '-INT', f"{p.pid}"])


def main():

    watcher = EndProcessWatcher()

    procs = start()
    
    while not watcher.kill_now:
        time.sleep(1)

    clean(procs)


main()