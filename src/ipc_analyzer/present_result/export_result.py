import sys
import os

from ipc_analyzer.present_result.parse_logs.parse_openat import parse_bpf_openat_logs
from ipc_analyzer.present_result.parse_logs.parse_close import parse_bpf_close_logs
from ipc_analyzer.present_result.parse_logs.parse_read import parse_bpf_read_logs
from ipc_analyzer.present_result.parse_logs.parse_write import parse_bpf_write_logs

from ipc_analyzer.present_result.postprocess_parse import add_stdios, normalize_events, normalize_timestamps, sort_events

from ipc_analyzer.present_result.ipca_globals import Event, GlobalModel, IPCAModel, Process, Resource

import json
from json import JSONEncoder

from pathlib import Path


class IPCAModelEncoder(JSONEncoder):
    def default(self, o):
        # Serialize the whole model: processes/resources as full objects, events as processed entries
        if isinstance(o, IPCAModel):
            return {
                'processes': [p.__dict__ for p in o.processes],
                'resources': [r.__dict__ for r in o.resources],
                'events': [self.default(e) for e in o.events]
            }

        # Top-level Process/Resource objects should be serialized fully
        if isinstance(o, Process):
            return o.__dict__
        elif isinstance(o, Resource):
            return o.__dict__

        # Events: replace any Process/Resource references with their index in the global lists
        elif isinstance(o, Event):
            serialized = {}
            for k, v in o.__dict__.items():
                # single Process
                if isinstance(v, Process):
                    serialized[k] = f"p:{GlobalModel.processes.index(v)}"
                # single Resource
                elif isinstance(v, Resource):
                    serialized[k] = f"r:{GlobalModel.resources.index(v)}"
                # list containing Processes/Resources (or mixed)
                elif isinstance(v, list):
                    new_list = []
                    for item in v:
                        if isinstance(item, Process):
                            new_list.append(f"p:{GlobalModel.processes.index(item)}")
                        elif isinstance(item, Resource):
                            new_list.append(f"r:{GlobalModel.resources.index(item)}")
                        else:
                            new_list.append(item)
                    serialized[k] = new_list
                else:
                    serialized[k] = v
            return serialized

        return super().default(o)



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

    sort_events()
    normalize_timestamps()
    add_stdios()
    normalize_events()

    Path(f"{root_dir}/present_result/output").mkdir(parents=True, exist_ok=True)

    with open(f"{root_dir}/present_result/output/{out_filename}", "w") as f:
        f.write(json.dumps(GlobalModel, indent=4, cls=IPCAModelEncoder))
    
    
if __name__ == '__main__':
    main()