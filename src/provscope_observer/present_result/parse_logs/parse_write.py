
from provscope_observer.present_result.ProvScopeGlobals import GlobalModel, ParsingResult, Process, WriteEvent
from provscope_observer.present_result.parse_logs.parse_globals import IGNORE_PATTERN, bpftrace_bufstr_to_bytestring, get_bpftrace_map


N_INFOS = 7


def parse_bpf_write_logs(filename: str) -> bool:
    
    write_events = get_bpftrace_map(filename, key="@write_events")
    if write_events is None:
        print(f"[PARSE_WRITE - ERROR] Could not find @write_events map in {filename}")
        return False
    
    write_buf = get_bpftrace_map(filename, key="@write_buf")
    if write_buf is None:
        print(f"[PARSE_WRITE - ERROR] Could not find @write_buf map in {filename}")
        return False

    for id, value in write_events.items():
        buffer = write_buf.get(f"{id}", "")
        write_events[id] = (*value, buffer)


    write_events = list(write_events.values())


    for i, event in enumerate(write_events):
        parsing_result = add_to_model(event)
        match parsing_result:
            case ParsingResult.ERR_COULD_NOT_PARSE:
                print(f"[PARSE_WRITE - ERROR] Could not parse event {i} properly : {event}")
                return False
            case ParsingResult.WARN_IGNORE_LINE:
                print(f"[PARSE_WRITE - WARNING] Ignoring event {i} : {event}")
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
        size,
        ret,
        content
    ) = event

    content = bpftrace_bufstr_to_bytestring(content)

    if any(name == ignore for ignore in IGNORE_PATTERN):
        return ParsingResult.WARN_IGNORE_LINE
    
    new_process = Process(pid, name)
    process = GlobalModel.add_or_get_process(new_process)

    write_event = WriteEvent(timestamp, f"{process.name}-{process.pid} writes to fd {fd}", process, fd, size, content, ret)
    GlobalModel.add_event(write_event)

    return ParsingResult.OK