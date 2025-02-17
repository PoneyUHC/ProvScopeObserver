
import os
import sys
import time

import subprocess

from ipc_analyzer.utils import EndProcessWatcher

ERR_BAD_ARG = 1


def start(n_targets: int):

    procs = []

    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)
    subprocess.run(['make', 'all', '-C', script_dir])

    os.chdir('./build/exec')

    for i in range(n_targets):
        with open(f"run/a{i}.logs", 'w') as fout:
            p = subprocess.Popen(['./target.bin', f'run/r_a{i}'], stdout=fout)
            procs.append(p)

    time.sleep(0.5)

    with open('run/log_c.logs', 'w') as fout:
        p = subprocess.Popen(['./log_collector.bin', 'run/att_l', 'run/logs', 'run/goal'], stdout=fout)
        procs.append(p)

    time.sleep(0.5)

    with open('run/router.logs', 'w') as fout:
        p = subprocess.Popen(['./router.bin', 'run/att_r', 'run/r_a1', 'run/r_a2', 'run/logs'], stdout=fout)
        procs.append(p)
    
    return procs


def clean(procs: list[subprocess.Popen]):

    for p in procs:
        p.terminate()


def main():

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <n_targets>")
        sys.exit(ERR_BAD_ARG)

    n_targets = int(sys.argv[1])
    if n_targets < 1 or n_targets > 5:
        print("Number of targets must be in at least 1, at most 5")
        sys.exit(ERR_BAD_ARG)

    watcher = EndProcessWatcher()

    procs = start(n_targets)
    
    while not watcher.kill_now:
        time.sleep(1)

    clean(procs)


main()