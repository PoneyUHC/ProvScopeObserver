import sys
import os
import time

from ipc_analyzer.present_result.parse_logs.parse_openat import parse_bpf_openat_logs
from ipc_analyzer.present_result.parse_logs.parse_close import parse_bpf_close_logs
from ipc_analyzer.present_result.parse_logs.parse_read import parse_bpf_read_logs
from ipc_analyzer.present_result.parse_logs.parse_write import parse_bpf_write_logs

from ipc_analyzer.present_result.postprocess_parse import add_stdios, normalize_events, normalize_timestamps, sort_events, add_color_information

from ipc_analyzer.present_result.ipca_globals import Entity, Event, GlobalModel, IPCAModel, Process, Resource

import json
from json import JSONEncoder

from pathlib import Path


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
    
    out_filename = 'report.json'
    if len(sys.argv) < 2:
        print(f"No specified export filename, defaulting to {out_filename}")
    else:
        out_filename = sys.argv[1]

    root_dir = os.path.dirname(os.path.dirname(__file__))
    
    start = time.time()

    parse_bpf_openat_logs(f"{root_dir}/trace/run/logs/trace_open.logs")
    parse_bpf_close_logs(f"{root_dir}/trace/run/logs/trace_close.logs")
    parse_bpf_read_logs(f"{root_dir}/trace/run/logs/trace_read.logs")
    parse_bpf_write_logs(f"{root_dir}/trace/run/logs/trace_write.logs")

    GlobalModel.events = list(filter(lambda e: e.event_type != "EnterReadEvent", GlobalModel.events))

    sort_events()
    normalize_timestamps()
    add_stdios()
    normalize_events()
    add_color_information()

    normalization_time = time.time() - start
    print(f"Normalization completed in {normalization_time:.2f} seconds")

    output_path = f"{root_dir}/present_result/output/{out_filename}"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(json.dumps(GlobalModel, indent=4, cls=IPCAModelEncoder))
    
    export_time = time.time() - start
    print(f"Export completed in {export_time:.2f} seconds")

    
if __name__ == '__main__':
    main()