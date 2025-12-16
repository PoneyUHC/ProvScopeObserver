#!/usr/bin/env python3
import os
import subprocess
import time

from ipc_analyzer.utils import EndProcessWatcher


def start() -> list[subprocess.Popen]:

    procs = []

    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)
    subprocess.run(['make', 'all', '-C', script_dir])

    ROOT = os.path.dirname(__file__)
    BUILD = os.path.join(ROOT, 'build', 'exec', 'run')
    os.makedirs(BUILD, exist_ok=True)

    router_bin = os.path.join(BUILD, 'router')
    user_bin = os.path.join(BUILD, 'user')
    auth_bin = os.path.join(BUILD, 'auth')

    fifo_att_to_u1 = os.path.join(BUILD, 'fifo_attacker_to_u1')
    fifo_att_to_u2 = os.path.join(BUILD, 'fifo_attacker_to_u2')
    fifo_u1_to = os.path.join(BUILD, 'fifo_u1_to_router')
    fifo_u2_to = os.path.join(BUILD, 'fifo_u2_to_router')
    fifo_router_u1 = os.path.join(BUILD, 'fifo_router_to_u1')
    fifo_router_u2 = os.path.join(BUILD, 'fifo_router_to_u2')
    fifo_router_auth = os.path.join(BUILD, 'fifo_router_to_auth')
    fifo_router_access = os.path.join(BUILD, 'fifo_router_to_access')
    fifo_access_router = os.path.join(BUILD, 'fifo_access_to_router')

    password_file = os.path.join(BUILD, 'password')
    allow_file = os.path.join(BUILD, 'allow')

    FS_ROOT = os.path.join(BUILD, 'fs/')
    policy_file = os.path.join(FS_ROOT, 'policy')
    os.makedirs(FS_ROOT, exist_ok=True)
    os.makedirs(os.path.join(FS_ROOT, 'user_1'), exist_ok=True)
    os.makedirs(os.path.join(FS_ROOT, 'user_2'), exist_ok=True)


    for p in [fifo_att_to_u1, fifo_att_to_u2, fifo_u1_to, fifo_u2_to, fifo_router_u1, fifo_router_u2, fifo_router_auth, fifo_router_access, fifo_access_router]:
        try:
            if os.path.exists(p):
                os.remove(p)
            os.mkfifo(p)
        except Exception as e:
            print('Could not create fifo', p, e)

    print('Starting router')
    with open(os.path.join(BUILD, 'router.logs'), 'w') as fout:
        router_proc = subprocess.Popen([router_bin, fifo_u1_to, fifo_u2_to, fifo_router_u1, fifo_router_u2, fifo_router_auth, allow_file, fifo_router_access, fifo_access_router], stdout=fout)
        procs.append(router_proc)

    # Give router time to open/write ends
    time.sleep(1)

    # create password file with per-user passwords
    # Format: <uid>:<password> per line
    with open(password_file, 'w') as f:
        f.write('1:user1_is_da_best\n')
        f.write('2:user2_is_better\n')

    with open(policy_file, 'w') as f:
        f.write('USER\n')
        f.write('1\n')
        f.write('user_2/\n')
        f.write('USER\n')
        f.write('2\n')
        f.write('user_1/\n')

    # ensure allow file exists and is empty
    open(allow_file, 'w').close()

    print('Starting auth process')
    with open(os.path.join(BUILD, 'auth.logs'), 'w') as fout:
        auth_proc = subprocess.Popen([auth_bin, fifo_router_auth, password_file, allow_file], stdout=fout)
        procs.append(auth_proc)

    print('Starting access process')
    with open(os.path.join(BUILD, 'access.logs'), 'w') as fout:
        access_proc = subprocess.Popen([os.path.join(BUILD, 'access'), fifo_router_access, fifo_access_router, allow_file, policy_file, FS_ROOT], stdout=fout)
        procs.append(access_proc)

    print('Starting user1')
    with open(os.path.join(BUILD, 'u1.logs'), 'w') as fout:
        # user 1 provides uid 1 and correct password
        u1_proc = subprocess.Popen([user_bin, fifo_u1_to, fifo_router_u1, fifo_att_to_u1], stdout=fout)
        procs.append(u1_proc)

    print('Starting user2')
    with open(os.path.join(BUILD, 'u2.logs'), 'w') as fout:
        # user 2 tries to access without auth, then wrong password, then correct
        u2_proc = subprocess.Popen([user_bin, fifo_u2_to, fifo_router_u2, fifo_att_to_u2], stdout=fout)
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