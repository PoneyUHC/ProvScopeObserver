
import sys
import json
import subprocess

from os import listdir
from os.path import isfile, isdir, join


ERR_USAGE = 1
ERR_INVALID_DIR = 2

INSTANCE_FILENAME = "my_instance.inst"
SOLUTION_FILENAME = "my_solution"
SOLVER_PATH = "~/cats-dev/cats-ts-lcs-fork/main.exe"
SOLVER_ARGS = ["10", "0", "50", "0", "3" , SOLUTION_FILENAME]


def call_solver(path, args, instance):
    print(f"Calling {[path, instance, *args]}")
    proc = subprocess.Popen(f"{path} {instance} {' '.join(args)}", shell=True)
    proc.wait()
    print("finished")

name_pid_uuid_map = {}

# we can't know which process is id1 or id2 across multiuple execs
# maybe would need the evaluator help on this
def get_process_unique_name(process):
    global name_pid_uuid_map
    
    name = process["name"]
    pid = process["pid"]
    
    if not name in name_pid_uuid_map.keys():
        name_pid_uuid_map[name] = {}
        name_pid_uuid_map[name][pid] = 0
    else:
        if not pid in name_pid_uuid_map[name].keys():
            name_pid_uuid_map[name][pid] = len(name_pid_uuid_map[name].keys())
            
    suffix = name_pid_uuid_map[name][pid]
            
    return f"{name}{suffix}"

def compress_event(trace, event):
    result = ""
    
    process_index = event["process"]
    process_uuid = get_process_unique_name(trace["processes"][process_index])
    
    match event["event_type"]:
        
        case "OpenEvent":
            file_index = event["file"]
            file_name = trace["files"][file_index]["path"] 
            result = f"{process_uuid}(open({file_name}))"

        case "CloseEvent":
            fd = event["fd"]
            result = f"{process_uuid}(close({fd}))"

        case "EnterReadEvent":
            fd = event["fd"]
            result = f"{process_uuid}(enters_read())"

        case "ExitReadEvent":
            fd = event["fd"]
            result = f"{process_uuid}(exits_read())"

        case "WriteEvent":
            fd = event["fd"]
            result = f"{process_uuid}(write())"

        case _:
            result = "error"
            
    return result


def load_and_compress_trace(trace_file):
    
    result = []
    
    with open(trace_file, 'r') as fin:
        content = "\n".join(fin.readlines())
        
        trace = json.loads(content)

        for event in trace["events"]:
            compressed_event = compress_event(trace, event)
            result.append(compressed_event)

    return result


def event_traces_to_indexed_traces(traces):
    
    indexed_traces = []
    current_indexed_trace = []
    index_map = {}
    current_index = 0
    
    for trace in traces:
        for event in trace:    
            if event in index_map.keys():
                current_indexed_trace.append(index_map[event])
            else:
                index_map[event] = current_index
                current_indexed_trace.append(current_index)
                current_index += 1
                
        indexed_traces.append(current_indexed_trace)
        current_indexed_trace = []
        
    return indexed_traces, current_index, index_map


def export_as_instance_format(indexed_traces, n_index, output_file):
    
    with open(output_file, 'w') as fout:
        header = f"{len(indexed_traces)} {n_index}\n"
        fout.write(header)
        
        for trace in indexed_traces:
            fout.write(f"{len(trace)}\n")
            body = " ".join(map(str, trace))
            fout.write(f"{body}\n")


def get_solution_file_content():
    
    # TODO: the solver automatically appends ".sol" at the end of solution filename
    # maybe pull request or fork to remove it
    with open(f"{SOLUTION_FILENAME}.sol", 'r') as fin:
        solution = list(map(int, fin.readline().strip().split(' ')))

    return solution


def indexed_trace_to_event_trace(indexed_solution, index_map):
    
    event_solution = []
    
    for index in indexed_solution:
        # TODO: use bidirectional map
        for key, value in index_map.items():
            if index == value:
                event_solution.append(key)
    
    
    return event_solution


def main():

    argv = sys.argv
    if len(argv) < 2:
        print(f"Usage : {argv[0]} [report_folder]")
        exit(ERR_USAGE)

    report_folder = argv[1]
    if not isdir(report_folder):
        print(f"{report_folder} : not a directory")
        exit(ERR_INVALID_DIR)

    files = [join(report_folder, f) for f in listdir(report_folder) if isfile(join(report_folder, f))]
    files.sort()
    
    if len(files) < 2:
        print(f"{report_folder} : not enough files to compare")

    compressed_traces = []
    for f in files:
        t = load_and_compress_trace(f)
        compressed_traces.append(t)
        name_pid_uuid_map.clear()
        
    indexed_traces, n_index, index_map = event_traces_to_indexed_traces(compressed_traces)

    export_as_instance_format(indexed_traces, n_index, INSTANCE_FILENAME)
    call_solver(SOLVER_PATH, SOLVER_ARGS, INSTANCE_FILENAME)
    
    indexed_solution = get_solution_file_content() 
    event_solution = indexed_trace_to_event_trace(indexed_solution, index_map)
    print("\n".join(event_solution))
    

if __name__ == '__main__':
    main()