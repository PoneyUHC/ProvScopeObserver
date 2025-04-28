
import os
import sys
import time

import subprocess

from ipc_analyzer.utils import EndProcessWatcher

ERR_BAD_ARG = 1


def start(n_clients: int):

    procs = []

    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)
    subprocess.run(['make', 'all', '-C', script_dir])

    os.chdir('./build/exec')

    router_to_clients = [f"run/r_client{i}" for i in range(n_clients)]
    clients_to_router = [f"run/client{i}_r" for i in range(n_clients)]

    with open('run/router.logs', 'w') as fout:
        p = subprocess.Popen(['./router.bin', 'run/logs', str(n_clients), *clients_to_router, *router_to_clients], stdout=fout)
        procs.append(p)

    for i in range(n_clients):
        with open(f"run/client{i}.logs", 'w') as fout:
            p = subprocess.Popen(['./client.bin', "1", router_to_clients[i], clients_to_router[i], str(n_clients), str(i)], stdout=fout)
            procs.append(p)

    with open('run/log_c.logs', 'w') as fout:
        p = subprocess.Popen(['./log_collector.bin', 'run/any_l', 'run/logs', 'run/goal'], stdout=fout)
        procs.append(p)
    
    return procs


def clean(procs: list[subprocess.Popen]):

    for p in procs:
        p.terminate()


def main():

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <n_targets>")
        sys.exit(ERR_BAD_ARG)

    n_clients = int(sys.argv[1])
    if n_clients < 1 or n_clients > 5:
        print("Number of targets must be in at least 1, at most 5")
        sys.exit(ERR_BAD_ARG)

    watcher = EndProcessWatcher()

    procs = start(n_clients)
    
    while not watcher.kill_now:
        time.sleep(0.2)

    clean(procs)


main()