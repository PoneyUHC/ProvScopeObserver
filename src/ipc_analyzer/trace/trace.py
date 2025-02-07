
import sys
import os
import time

from subprocess import Popen, run

ERR_BAD_ARG = 1


def main():

    if len(sys.argv) != 2:
        print("Usage: trace.py <arg>")
        sys.exit(ERR_BAD_ARG)

    procs = []

    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)

    with open('logs/trace_open.logs', 'w') as fout:
        p = Popen(['bpftrace', 'trace_open.bt', sys.argv[1]], stdout=fout)
        procs.append(p)

    with open('logs/trace_close.logs', 'w') as fout:
        p = Popen(['bpftrace', 'trace_close.bt', sys.argv[1]], stdout=fout)
        procs.append(p)

    with open('logs/trace_write.logs', 'w') as fout:
        p = Popen(['bpftrace', 'trace_write.bt', sys.argv[1]], stdout=fout)
        procs.append(p)

    with open('logs/trace_read.logs', 'w') as fout:
        p = Popen(['bpftrace', 'trace_read.bt', sys.argv[1]], stdout=fout)
        procs.append(p)

    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()