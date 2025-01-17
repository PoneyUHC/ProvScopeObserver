
import sys
import json

from os import listdir
from os.path import isfile, isdir, join


ERR_USAGE = 1
ERR_INVALID_DIR = 2

def preprocess_trace(trace_file):
    trace = json.loads(trace_file)

    for e in trace["events"]:
        pass


def main():

    argv = sys.argv
    if len(argv) < 2:
        print(f"Usage : {argv[0]} [report_folder]")
        exit(ERR_USAGE)

    report_folder = argv[1]
    if not isdir(report_folder):
        print(f"{report_folder} : no such directory")
        exit(ERR_INVALID_DIR)

    files = [f for f in listdir(report_folder) if isfile(join(report_folder, f))]
    
    if len(files) < 2:
        print(f"{report_folder} : not enough files to compare")

    traces = []
    for f in files:
        t = preprocess_trace(f)
        traces.append(t)


    preprocess_trace()


if __name__ == '__main__':
    main()