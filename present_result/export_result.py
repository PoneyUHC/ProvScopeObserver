
import sys

from parse_logs.parse_openat import parse_bpf_openat_logs
from parse_logs.parse_close import parse_bpf_close_logs
from parse_logs.parse_read import parse_bpf_read_logs
from parse_logs.parse_write import parse_bpf_write_logs

from postprocess_parse import unify_bpf_logs, sort_events

from ipca_globals import GlobalModel, Process, File, OpenInfo, CommunicationChannel

import json
from json import JSONEncoder

from pathlib import Path

O_RDONLY = 0
O_WRONLY = 1
O_RDWR = 2

class MyEncoder(JSONEncoder):
    def default(self, o):
        patched_dict = {}
        for key, value in o.__dict__.items():
            if isinstance(value, Process):
                patched_dict[key] = GlobalModel.processes.index(value)
            elif isinstance(value, CommunicationChannel):
                patched_dict[key] = GlobalModel.channels.index(value)
            elif isinstance(value, File):
                patched_dict[key] = GlobalModel.files.index(value)
            else:
                patched_dict[key] = value
        return patched_dict
    

def main():
    
    out_filename = 'model.json'
    if len(sys.argv) < 2:
        print("No specified export filename, defaulting to 'model.json'")
    else:
        out_filename = sys.argv[1]
    
    parse_bpf_openat_logs("trace/logs/trace_open.logs")
    parse_bpf_close_logs("trace/logs/trace_close.logs")
    parse_bpf_read_logs("trace/logs/trace_read.logs")
    parse_bpf_write_logs("trace/logs/trace_write.logs")

    unify_bpf_logs()
    sort_events()

    Path("present_result/output").mkdir(parents=True, exist_ok=True)

    with open(f"present_result/output/{out_filename}", "w") as f:
        f.write(json.dumps(GlobalModel, indent=4, cls=MyEncoder))
    
    
if __name__ == '__main__':
    main()