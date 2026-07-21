#!/usr/bin/env python3
import os
import subprocess
import time

from provscope_observer.utils import EndProcessWatcher


def start() -> list[subprocess.Popen]:

    procs = []

    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)
    subprocess.run(['make', 'all', '-C', script_dir])

    ROOT = os.path.dirname(__file__)
    BUILD = os.path.join(ROOT, 'build', 'exec')
    os.makedirs(BUILD, exist_ok=True)

    router_bin = os.path.join(BUILD, 'router')
    user_bin = os.path.join(BUILD, 'user')
    auth_bin = os.path.join(BUILD, 'auth')

    RUN_DIR = os.path.join(BUILD, 'run')
    os.makedirs(RUN_DIR, exist_ok=True)

    LOGS_DIR = os.path.join(RUN_DIR, 'logs')
    os.makedirs(LOGS_DIR, exist_ok=True)

    FS_ROOT = os.path.join(RUN_DIR, 'fs/')
    COMMS_DIR = os.path.join(FS_ROOT, 'comms/')
    fifo_comm_to_u1 = os.path.join(COMMS_DIR, 'fifo_comm_to_u1')
    fifo_comm_to_u2 = os.path.join(COMMS_DIR, 'fifo_comm_to_u2')
    fifo_comm_to_admin = os.path.join(COMMS_DIR, 'fifo_comm_to_admin')
    fifo_u1_to_router = os.path.join(COMMS_DIR, 'fifo_u1_to_router')
    fifo_u2_to_router = os.path.join(COMMS_DIR, 'fifo_u2_to_router')
    fifo_admin_to_router = os.path.join(COMMS_DIR, 'fifo_admin_to_router')
    fifo_router_u1 = os.path.join(COMMS_DIR, 'fifo_router_to_u1')
    fifo_router_u2 = os.path.join(COMMS_DIR, 'fifo_router_to_u2')
    fifo_router_admin = os.path.join(COMMS_DIR, 'fifo_router_to_admin')
    fifo_router_auth = os.path.join(COMMS_DIR, 'fifo_router_to_auth')
    fifo_auth_router = os.path.join(COMMS_DIR, 'fifo_auth_to_router')
    fifo_router_access = os.path.join(COMMS_DIR, 'fifo_router_to_access')
    fifo_access_router = os.path.join(COMMS_DIR, 'fifo_access_to_router')

    MISC_DIR = os.path.join(FS_ROOT, 'misc/')
    password_file = os.path.join(MISC_DIR, 'password')
    allow_file = os.path.join(MISC_DIR, 'allow')

    policy_file = os.path.join(FS_ROOT, 'policy')

    os.makedirs(FS_ROOT, exist_ok=True)
    os.makedirs(MISC_DIR, exist_ok=True)
    os.makedirs(COMMS_DIR, exist_ok=True)
    os.makedirs(os.path.join(FS_ROOT, 'user_1'), exist_ok=True)
    os.makedirs(os.path.join(FS_ROOT, 'user_2'), exist_ok=True)


    for p in [fifo_comm_to_u1, fifo_comm_to_u2, fifo_comm_to_admin, fifo_u1_to_router, fifo_u2_to_router, fifo_admin_to_router, fifo_router_u1, fifo_router_u2, fifo_router_admin, fifo_router_auth, fifo_router_access, fifo_auth_router, fifo_access_router]:
        try:
            if os.path.exists(p):
                os.remove(p)
            os.mkfifo(p)
        except Exception as e:
            print('Could not create fifo', p, e)

    print('Starting router')
    with open(os.path.join(LOGS_DIR, 'router.logs'), 'w') as fout:
        router_proc = subprocess.Popen([router_bin, fifo_u1_to_router, fifo_u2_to_router, fifo_admin_to_router, fifo_router_u1, fifo_router_u2, fifo_router_admin, fifo_router_auth, fifo_auth_router, fifo_router_access, fifo_access_router], stdout=fout)
        procs.append(router_proc)

    # create password file with per-user passwords
    # Format: <uid>:<password> per line
    with open(password_file, 'w') as f:
        f.write('1:user1_is_da_best\n')
        f.write('2:user2_is_better\n')
        f.write('3:admin_the_goat\n')

    with open(policy_file, 'w') as f:
        f.write('USER\n')
        f.write('1\n')
        f.write('comms/\n')
        f.write('misc/\n')
        f.write('user_2/\n')
        f.write('USER\n')
        f.write('2\n')
        f.write('misc/\n')
        f.write('comms/\n')
        f.write('user_1/\n')

    # ensure allow file exists and is empty
    open(allow_file, 'w').close()

    print('Starting auth process')
    with open(os.path.join(LOGS_DIR, 'auth.logs'), 'w') as fout:
        auth_proc = subprocess.Popen([auth_bin, fifo_router_auth, fifo_auth_router, password_file, allow_file], stdout=fout)
        procs.append(auth_proc)

    print('Starting access process')
    with open(os.path.join(LOGS_DIR, 'access.logs'), 'w') as fout:
        access_proc = subprocess.Popen([os.path.join(BUILD, 'access'), fifo_router_access, fifo_access_router, allow_file, policy_file, FS_ROOT], stdout=fout)
        procs.append(access_proc)

    print('Starting user1')
    with open(os.path.join(LOGS_DIR, 'u1.logs'), 'w') as fout:
        # user 1 provides uid 1 and correct password
        u1_proc = subprocess.Popen([user_bin, fifo_u1_to_router, fifo_router_u1, fifo_comm_to_u1], stdout=fout)
        procs.append(u1_proc)

    print('Starting user2')
    with open(os.path.join(LOGS_DIR, 'u2.logs'), 'w') as fout:
        # user 2 tries to access without auth, then wrong password, then correct
        u2_proc = subprocess.Popen([user_bin, fifo_u2_to_router, fifo_router_u2, fifo_comm_to_u2], stdout=fout)
        procs.append(u2_proc)

    print('Starting admin')
    with open(os.path.join(LOGS_DIR, 'admin.logs'), 'w') as fout:
        # user 2 tries to access without auth, then wrong password, then correct
        u2_proc = subprocess.Popen([user_bin, fifo_admin_to_router, fifo_router_admin, fifo_comm_to_admin], stdout=fout)
        procs.append(u2_proc)

    print('Done.')
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