
from provscope_observer.present_result.ProvScopeGlobals import GlobalModel, Process, Resource, ParsingResult, OpenEvent, ResourceType
from provscope_observer.present_result.parse_logs.parse_globals import EXT_USTACKS, IGNORE_PATTERN, gather_ustacks, get_bpftrace_map


N_INFOS = 8


def parse_bpf_openat_logs(filename: str) -> bool:
    
    open_events_arguments_by_id = get_bpftrace_map(filename, key="@open_events")
    if open_events_arguments_by_id is None:
        print(f"[PARSE_OPEN - ERROR] Could not find @open_events map in {filename}")
        return False
    
    open_filenames_by_id = get_bpftrace_map(filename, key="@filename")
    if open_filenames_by_id is None:
        print(f"[PARSE_OPEN - ERROR] Could not find @filenames map in {filename}")
        return False
    

    for id, value in open_events_arguments_by_id.items():

        open_filename = open_filenames_by_id.get(id)
        if open_filename is None:
            print(f"[PARSE_OPEN - WARNING] Found open event with id {id} but no corresponding filename. Ignoring.")
            continue

        open_events_arguments_by_id[id] = (*value, open_filename)

    open_events_by_id = dict()
    for id, open_event_arguments in open_events_arguments_by_id.items():
        parsing_result, open_event = add_to_model(open_event_arguments)
        match parsing_result:
            case ParsingResult.ERR_COULD_NOT_PARSE:
                print(f"[PARSE_OPEN - ERROR] Could not parse event {id} properly : {open_event_arguments}")
                print(f"-----> Expected {N_INFOS} infos, got {len(open_event_arguments)}")
                return False
            case ParsingResult.WARN_IGNORE_LINE:
                print(f"[PARSE_OPEN - WARNING] Ignoring event {id} : {open_event_arguments}")
                continue
            case ParsingResult.OK:
                open_events_by_id[id] = open_event

    if EXT_USTACKS:
        gather_ustacks(filename, open_events_by_id)
        
    return True


def add_to_model(event: tuple) -> int:

    if len(event) != N_INFOS:
        return ParsingResult.ERR_COULD_NOT_PARSE, None

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
        return ParsingResult.WARN_IGNORE_LINE, None

    new_process = Process(pid, name)
    process = GlobalModel.add_or_get_process(new_process)

    new_resource = Resource(filepath, ResourceType.from_octal(resource_type))
    resource = GlobalModel.add_or_get_resource(new_resource)

    open_event = OpenEvent(timestamp, f"{process.name}-{process.pid} opens {resource.path} with fd {fd}", process, resource, fd, mode, access_mode)
    GlobalModel.add_event(open_event)

    return ParsingResult.OK, open_event