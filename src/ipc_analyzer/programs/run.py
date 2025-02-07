
import os
import time

from subprocess import Popen, run

ERR_BAD_ARG = 1


def main():

    procs = []

    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)
    run(['make', 'all', '-C', script_dir])

    os.chdir('./build/exec')

    with open('run/a1.logs', 'w') as fout:
        p = Popen(['./target.bin', 'run/r_a1'], stdout=fout)
        procs.append(p)

    time.sleep(0.5)

    with open('run/a2.logs', 'w') as fout:
        p = Popen(['./target.bin', 'run/r_a2'], stdout=fout)
        procs.append(p)

    time.sleep(0.5)

    with open('run/log_c.logs', 'w') as fout:
        p = Popen(['./log_collector.bin', 'run/att_l', 'run/logs', 'run/goal'], stdout=fout)
        procs.append(p)

    time.sleep(0.5)

    with open('run/a1.logs', 'w') as fout:
        p = Popen(['./router.bin', 'run/att_r', 'run/r_a1', 'run/r_a2', 'run/logs'], stdout=fout)
        procs.append(p)
    
    
    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()