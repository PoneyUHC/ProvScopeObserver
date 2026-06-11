
from provscope_observer.present_result.ProvScopeGlobals import GlobalModel, ParsingResult, Process, EnterReadEvent, ExitReadEvent
from provscope_observer.present_result.parse_logs.parse_globals import EXT_USTACKS, IGNORE_PATTERN, bpftrace_bufstr_to_bytestring, gather_ustacks, get_bpftrace_map


N_INFOS_ENTER = 5
N_INFOS_EXIT = 7


def parse_bpf_read_logs(filename: str) -> bool:
    
    enter_events_arguments_by_id = get_bpftrace_map(filename, key="@enter_events")
    if enter_events_arguments_by_id is None:
        print(f"[PARSE_READ - ERROR] Could not find @enter_events map in {filename}")
        return False

    exit_events_arguments_by_id = get_bpftrace_map(filename, key="@exit_events")
    if exit_events_arguments_by_id is None:
        print(f"[PARSE_READ - ERROR] Could not find @exit_events map in {filename}")
        return False
    
    read_buf_by_id = get_bpftrace_map(filename, key="@read_buf")
    if read_buf_by_id is None:
        print(f"[PARSE_READ - ERROR] Could not find @read_buf map in {filename}")
        return False

    for id, value in exit_events_arguments_by_id.items():
        if id not in enter_events_arguments_by_id:
            print(f"[PARSE_READ - WARNING] Found exit event with id {id} but no corresponding enter event. Ignoring.")
            continue

        buffer = read_buf_by_id.get(f"{id}", "")
        exit_events_arguments_by_id[id] = (*value, buffer)

    enter_read_events_by_id = dict()
    for id, event in enter_events_arguments_by_id.items():
        parsing_result, enter_read_event = add_enter_to_model(event)
        match parsing_result:
            case ParsingResult.ERR_COULD_NOT_PARSE:
                print(f"[PARSE_READ - ERROR] Could not parse event {id} properly : {event}")
                return False
            case ParsingResult.WARN_IGNORE_LINE:
                print(f"[PARSE_READ - WARNING] Ignoring event {id} : {event}")
                continue
            case ParsingResult.OK:
                enter_read_events_by_id[id] = enter_read_event


    exit_read_events_by_id = dict()
    for id, event in exit_events_arguments_by_id.items():
        parsing_result, exit_read_event = add_exit_to_model(event)
        match parsing_result:
            case ParsingResult.ERR_COULD_NOT_PARSE:
                print(f"[PARSE_READ - ERROR] Could not parse event {id} properly : {event}")
                return False
            case ParsingResult.WARN_IGNORE_LINE:
                print(f"[PARSE_READ - WARNING] Ignoring event {id} : {event}")
                continue
            case ParsingResult.OK:
                exit_read_events_by_id[id] = exit_read_event

    if EXT_USTACKS:
        gather_ustacks(filename, exit_read_events_by_id)
        gather_ustacks(filename, enter_read_events_by_id)

    return True


def add_exit_to_model(event: tuple) -> tuple[int, ExitReadEvent | None]:
    
    if len(event) not in [N_INFOS_ENTER, N_INFOS_EXIT]:
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

    exit_read_event = ExitReadEvent(timestamp, f"{process.name}-{process.pid} finishes reading from fd {fd}", process, fd, size, content, ret)
    GlobalModel.add_event(exit_read_event)
    
    return ParsingResult.OK, exit_read_event


def add_enter_to_model(event: tuple) -> tuple[int, EnterReadEvent | None]:

    if len(event) not in [N_INFOS_ENTER, N_INFOS_EXIT]:
        return ParsingResult.ERR_COULD_NOT_PARSE, None

    (
        timestamp,
        name,
        pid,
        fd,
        size,
    ) = event

    if any(name == ignore for ignore in IGNORE_PATTERN):
        return ParsingResult.WARN_IGNORE_LINE, None
    
    new_process = Process(pid, name)
    process = GlobalModel.add_or_get_process(new_process)

    enter_read_event = EnterReadEvent(timestamp, f"{process.name}-{process.pid} starts reading from fd {fd}", process, fd, size)
    GlobalModel.add_event(enter_read_event)

    return ParsingResult.OK, enter_read_event