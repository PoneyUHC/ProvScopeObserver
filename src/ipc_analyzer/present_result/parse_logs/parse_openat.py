
from ipc_analyzer.present_result.ipca_globals import GlobalModel, Process, Resource, ParsingResult, OpenEvent, ResourceType
from ipc_analyzer.present_result.parse_logs.parse_globals import IGNORE_PATTERN, bpftrace_to_IPCA


N_INFOS = 8


def parse_bpf_openat_logs(filename: str) -> bool:
    
    open_events = bpftrace_to_IPCA(filename, keys=["@open_events", "@filename"], merge=True)
    if not open_events:
        return False

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
        path,
        timestamp,
        name,
        pid,
        fd,
        mode,
        access_mode,
        resource_type
    ) = event

    if any(name == ignore for ignore in IGNORE_PATTERN):
        return ParsingResult.WARN_IGNORE_LINE

    new_process = Process(pid, name)
    process = GlobalModel.add_or_get_process(new_process)

    new_resource = Resource(path, ResourceType.from_octal(resource_type))
    resource = GlobalModel.add_or_get_resource(new_resource)

    open_event = OpenEvent(timestamp, f"{process.name}-{process.pid} opens {resource.path} with fd {fd}", process, resource, fd, mode, access_mode)
    GlobalModel.add_event(open_event)

    return ParsingResult.OK