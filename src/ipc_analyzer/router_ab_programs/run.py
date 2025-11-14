
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

    request_fifo = "run/request"
    router_to_a = "run/router_to_a"
    router_to_b = "run/router_to_b"
    allow_file = "run/allow"
    goal_file = "run/goal"

    # Create run directory
    os.makedirs('run', exist_ok=True)
    
    # Erase all log files from previous runs
    log_files = ['run/router.logs', 'run/router.err', 'run/process_a.logs', 'run/process_b.logs']
    for log_file in log_files:
        if os.path.exists(log_file):
            os.remove(log_file)
            print(f"Removed old log file: {log_file}")
    if not os.path.exists(request_fifo):
        os.mkfifo(request_fifo)
    if not os.path.exists(router_to_a):
        os.mkfifo(router_to_a)
    if not os.path.exists(router_to_b):
        os.mkfifo(router_to_b)

    router_log_path = 'run/router.logs'
    router_err_path = 'run/router.err'
    
    print(f"Starting router with args: {request_fifo}, {router_to_a}, {router_to_b}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Router binary exists: {os.path.exists('./router.bin')}")
    
    with open(router_log_path, 'a') as fout, open(router_err_path, 'a') as ferr:
        fout.write("=== Router starting ===\n")
        fout.flush()
        p = subprocess.Popen(['./router.bin', request_fifo, router_to_a, router_to_b], 
                           stdout=fout, stderr=ferr, cwd=os.getcwd())
        procs.append(p)
        fout.write(f"Router process started with PID: {p.pid}\n")
        fout.flush()
        print(f"Router process started with PID: {p.pid}")
        
        # Give router a moment to start and log
        time.sleep(0.1)
        
        # Check if router is still running
        if p.poll() is not None:
            print(f"ERROR: Router process exited immediately with code {p.returncode}")
            # Read what was logged
            fout.seek(0)
            ferr.seek(0)
            print("Router stdout:", fout.read())
            print("Router stderr:", ferr.read())

    # Wait for router to create FIFOs and initialize
    # The router will block on opening FIFOs for writing until readers connect
    time.sleep(0.5)
    
    # Verify FIFOs exist before starting processes
    if not os.path.exists(router_to_a) or not os.path.exists(router_to_b):
        print(f"Error: FIFOs not created. router_to_a exists: {os.path.exists(router_to_a)}, router_to_b exists: {os.path.exists(router_to_b)}")
        return procs

    with open('run/process_a.logs', 'w') as fout:
        p = subprocess.Popen(['./process_a.bin', router_to_a, allow_file], stdout=fout)
        procs.append(p)

    with open('run/process_b.logs', 'w') as fout:
        p = subprocess.Popen(['./process_b.bin', router_to_b, allow_file, goal_file], stdout=fout)
        procs.append(p)
    
    return procs


def clean(procs: list[subprocess.Popen]):

    for p in procs:
        p.terminate()


def main():

    watcher = EndProcessWatcher()

    procs = start()
    
    while not watcher.kill_now:
        time.sleep(0.2)

    clean(procs)


main()

