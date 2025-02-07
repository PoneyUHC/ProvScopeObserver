
import os
import time

import subprocess

from ipc_analyzer.utils import EndProcessWatcher

ERR_BAD_ARG = 1


def start():

    procs = []

    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)
    subprocess.run(['make', 'all', '-C', script_dir])

    os.chdir('./build/exec')

    with open('run/a1.logs', 'w') as fout:
        p = subprocess.Popen(['./target.bin', 'run/r_a1'], stdout=fout)
        procs.append(p)

    time.sleep(0.5)

    with open('run/a2.logs', 'w') as fout:
        p = subprocess.Popen(['./target.bin', 'run/r_a2'], stdout=fout)
        procs.append(p)

    time.sleep(0.5)

    with open('run/log_c.logs', 'w') as fout:
        p = subprocess.Popen(['./log_collector.bin', 'run/att_l', 'run/logs', 'run/goal'], stdout=fout)
        procs.append(p)

    time.sleep(0.5)

    with open('run/a1.logs', 'w') as fout:
        p = subprocess.Popen(['./router.bin', 'run/att_r', 'run/r_a1', 'run/r_a2', 'run/logs'], stdout=fout)
        procs.append(p)
    
    return procs


def clean(procs: list[subprocess.Popen]):

    for p in procs:
        p.terminate()


def main():

    watcher = EndProcessWatcher()

    procs = start()
    
    while not watcher.kill_now:
        time.sleep(1)

    clean(procs)


main()