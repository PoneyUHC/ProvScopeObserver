
import sys
import os

from ipc_analyzer.present_result.parse_logs.parse_openat import parse_bpf_openat_logs
from ipc_analyzer.present_result.parse_logs.parse_close import parse_bpf_close_logs
from ipc_analyzer.present_result.parse_logs.parse_read import parse_bpf_read_logs
from ipc_analyzer.present_result.parse_logs.parse_write import parse_bpf_write_logs

from ipc_analyzer.present_result.postprocess_parse import add_stdios, normalize_resources, normalize_timestamps, sort_events

from ipc_analyzer.present_result.ipca_globals import GlobalModel, Process, Resource

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
            elif isinstance(value, Resource):
                patched_dict[key] = GlobalModel.resources.index(value)
            else:
                patched_dict[key] = value
        return patched_dict
    

def main():
    
    out_filename = 'report.json'
    if len(sys.argv) < 2:
        print(f"No specified export filename, defaulting to {out_filename}")
    else:
        out_filename = sys.argv[1]

    root_dir = os.path.dirname(os.path.dirname(__file__))
    
    parse_bpf_openat_logs(f"{root_dir}/trace/logs/trace_open.logs")
    parse_bpf_close_logs(f"{root_dir}/trace/logs/trace_close.logs")
    parse_bpf_read_logs(f"{root_dir}/trace/logs/trace_read.logs")
    parse_bpf_write_logs(f"{root_dir}/trace/logs/trace_write.logs")

    add_stdios()
    sort_events()
    normalize_timestamps()
    normalize_resources()

    Path(f"{root_dir}/present_result/output").mkdir(parents=True, exist_ok=True)

    with open(f"{root_dir}/present_result/output/{out_filename}", "w") as f:
        f.write(json.dumps(GlobalModel, indent=4, cls=MyEncoder))
    
    
if __name__ == '__main__':
    main()