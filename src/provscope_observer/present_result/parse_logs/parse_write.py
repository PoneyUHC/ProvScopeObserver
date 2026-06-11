
from provscope_observer.present_result.ProvScopeGlobals import GlobalModel, ParsingResult, Process, WriteEvent
from provscope_observer.present_result.parse_logs.parse_globals import EXT_USTACKS, IGNORE_PATTERN, bpftrace_bufstr_to_bytestring, gather_ustacks, get_bpftrace_map


N_INFOS = 7


def parse_bpf_write_logs(filename: str) -> bool:
    
    write_events_arguments_by_id = get_bpftrace_map(filename, key="@write_events")
    if write_events_arguments_by_id is None:
        print(f"[PARSE_WRITE - ERROR] Could not find @write_events map in {filename}")
        return False
    
    write_buf_by_id = get_bpftrace_map(filename, key="@write_buf")
    if write_buf_by_id is None:
        print(f"[PARSE_WRITE - ERROR] Could not find @write_buf map in {filename}")
        return False

    for id, value in write_events_arguments_by_id.items():
        buffer = write_buf_by_id.get(f"{id}", "")
        write_events_arguments_by_id[id] = (*value, buffer)

    write_events_by_id = dict()
    for id, event in write_events_arguments_by_id.items():
        parsing_result, write_event = add_to_model(event)
        match parsing_result:
            case ParsingResult.ERR_COULD_NOT_PARSE:
                print(f"[PARSE_WRITE - ERROR] Could not parse event {id} properly : {event}")
                return False
            case ParsingResult.WARN_IGNORE_LINE:
                print(f"[PARSE_WRITE - WARNING] Ignoring event {id} : {event}")
                continue
            case ParsingResult.OK:
                write_events_by_id[id] = write_event
        

    if EXT_USTACKS:
        gather_ustacks(filename, write_events_by_id)

    return True


def add_to_model(event: tuple) -> tuple[int, WriteEvent | None]:

    if len(event) != N_INFOS:
        return ParsingResult.ERR_COULD_NOT_PARSE, None

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
        return ParsingResult.WARN_IGNORE_LINE, None
    
    new_process = Process(pid, name)
    process = GlobalModel.add_or_get_process(new_process)

    write_event = WriteEvent(timestamp, f"{process.name}-{process.pid} writes to fd {fd}", process, fd, size, content, ret)
    GlobalModel.add_event(write_event)

    return ParsingResult.OK, write_event