import sys

from ipc_analyzer.present_result.parse_logs.parse_openat import parse_bpf_openat_logs
from ipc_analyzer.present_result.parse_logs.parse_close import parse_bpf_close_logs
from ipc_analyzer.present_result.parse_logs.parse_read import parse_bpf_read_logs
from ipc_analyzer.present_result.parse_logs.parse_write import parse_bpf_write_logs

from ipc_analyzer.present_result.postprocess_parse import add_stdios, normalize_events, normalize_timestamps, sort_events, add_color_information

from ipc_analyzer.present_result.ipca_globals import Entity, Event, GlobalModel, IPCAModel, Process, Resource

import json
from json import JSONEncoder

from pathlib import Path

DEFAULT_TRACE_BACKEND = "bpftrace024"


def get_trace_logs_dir(root_dir: str, backend: str) -> Path:
    return Path(root_dir) / "trace" / "run" / backend / "logs"


def serialize_lookup(object: int | str | Entity):
    if isinstance(object, Process):
        return f"p:{GlobalModel.processes.index(object)}"
    elif isinstance(object, Resource):
        return f"r:{GlobalModel.resources.index(object)}"
    else:
        return object
    

def serialize_event(event: Event):
    if not isinstance(event, Event):
        print(f"[EXPORT - FATAL] Unexpected object during export: {event}") 
        return 
        
    serialized = {
        "event_type" : event.event_type,
        "timestamp" : event.timestamp,
        "description" : event.description,
        "process" : serialize_lookup(event.process),
        "other_entities" : [serialize_lookup(e) for e in event.other_entities],
        "source_entities" : [serialize_lookup(e) for e in event.source_entities],
        "target_entities" : [serialize_lookup(e) for e in event.target_entities],
        "input_values" : event.input_values,
        "output_values" : event.output_values
    }

    return serialized


class IPCAModelEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, IPCAModel):
            return {
                'processes': [p.__dict__ for p in o.processes],
                'resources': [r.__dict__ for r in o.resources],
                'events': [serialize_event(e) for e in o.events],
                '_extensions' : [
                    {
                        "tag": "EXT_EVENT_COLOR",
                        "data": o.ext_colors
                    }
                ]
                    
            }
        else:
            print(f"[EXPORT - FATAL] Given object is not an IPCAModel: {o}")
            return None


def main():
    
    monitor_version = DEFAULT_TRACE_BACKEND
    out_filename = 'report.json'
    if len(sys.argv) >= 3:
        monitor_version = sys.argv[1]
        out_filename = sys.argv[2]
    elif len(sys.argv) == 2:
        out_filename = sys.argv[1]
    else:
        print(f"No specified export filename, defaulting to {out_filename}")

    root_dir = Path(__file__).resolve().parent.parent
    
    logs_dir = get_trace_logs_dir(str(root_dir), monitor_version)

    parse_bpf_openat_logs(str(logs_dir / "trace_open.logs"))
    parse_bpf_close_logs(str(logs_dir / "trace_close.logs"))
    parse_bpf_read_logs(str(logs_dir / "trace_read.logs"))
    parse_bpf_write_logs(str(logs_dir / "trace_write.logs"))

    GlobalModel.events = list(filter(lambda e: e.event_type != "EnterReadEvent", GlobalModel.events))

    sort_events()
    normalize_timestamps()
    add_stdios()
    normalize_events()
    add_color_information()

    output_path = f"{root_dir}/present_result/output/{out_filename}"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(json.dumps(GlobalModel, indent=4, cls=IPCAModelEncoder))
    
    
if __name__ == '__main__':
    main()
