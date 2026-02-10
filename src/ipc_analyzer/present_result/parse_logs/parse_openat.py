
from ipc_analyzer.present_result.ipca_globals import GlobalModel, Process, Resource, ParsingResult, OpenEvent, ResourceType
from ipc_analyzer.present_result.parse_logs.parse_globals import IGNORE_PATTERN, get_bpftrace_map


N_INFOS = 8


def parse_bpf_openat_logs(filename: str) -> bool:
    
    open_events = get_bpftrace_map(filename, key="@open_events")
    if open_events is None:
        print(f"[PARSE_OPEN - ERROR] Could not find @open_events map in {filename}")
        return False
    
    filenames = get_bpftrace_map(filename, key="@filename")
    if filenames is None:
        print(f"[PARSE_OPEN - ERROR] Could not find @filenames map in {filename}")
        return False
    

    for id, value in open_events.items():

        filename = filenames.get(id)
        if filename is None:
            print(f"[PARSE_OPEN - WARNING] Found open event with id {id} but no corresponding filename. Ignoring.")
            continue

        open_events[id] = (*value, filename)

    open_events = list(open_events.values())


    for i, event in enumerate(open_events):
        parsing_result = add_to_model(event)
        match parsing_result:
            case ParsingResult.ERR_COULD_NOT_PARSE:
                print(f"[PARSE_OPEN - ERROR] Could not parse event {i} properly : {event}")
                print(f"-----> Expected {N_INFOS} infos, got {len(event)}")
                return False
            case ParsingResult.WARN_IGNORE_LINE:
                print(f"[PARSE_OPEN - WARNING] Ignoring event {i} : {event}")
                continue
            case ParsingResult.OK:
                continue
        
    return True


def add_to_model(event: tuple) -> int:

    if len(event) != N_INFOS:
        return ParsingResult.ERR_COULD_NOT_PARSE

    (
        timestamp,
        name,
        pid,
        fd,
        mode,
        access_mode,
        resource_type,
        filepath
    ) = event

    if any(name == ignore for ignore in IGNORE_PATTERN):
        return ParsingResult.WARN_IGNORE_LINE

    new_process = Process(pid, name)
    process = GlobalModel.add_or_get_process(new_process)

    new_resource = Resource(filepath, ResourceType.from_octal(resource_type))
    resource = GlobalModel.add_or_get_resource(new_resource)

    open_event = OpenEvent(timestamp, f"{process.name}-{process.pid} opens {resource.path} with fd {fd}", process, resource, fd, mode, access_mode)
    GlobalModel.add_event(open_event)

    return ParsingResult.OK