
from ipc_analyzer.present_result.ipca_globals import GlobalModel, ParsingResult, Process, EnterReadEvent, ExitReadEvent
from ipc_analyzer.present_result.parse_logs.parse_globals import IGNORE_PATTERN, get_bpftrace_map


N_INFOS_ENTER = 5
N_INFOS_EXIT = 7


def parse_bpf_read_logs(filename: str) -> bool:
    
    enter_events = get_bpftrace_map(filename, key="@enter_events")
    if enter_events is None:
        print(f"[PARSE_READ - ERROR] Could not find @enter_events map in {filename}")
        return False

    exit_events = get_bpftrace_map(filename, key="@exit_events")
    if exit_events is None:
        print(f"[PARSE_READ - ERROR] Could not find @exit_events map in {filename}")
        return False
    
    read_buf = get_bpftrace_map(filename, key="@read_buf")
    if read_buf is None:
        print(f"[PARSE_READ - ERROR] Could not find @read_buf map in {filename}")
        return False

    for id, value in exit_events.items():
        if id not in enter_events:
            print(f"[PARSE_READ - WARNING] Found exit event with id {id} but no corresponding enter event. Ignoring.")
            continue

        buffer = []
        byte_idx = 0
        while read_buf.get(f"{id},{byte_idx}") is not None:
            buffer.append(read_buf[f"{id},{byte_idx}"])
            byte_idx += 1

        exit_events[id] = (*value, buffer)


    enter_events = list(enter_events.values())
    exit_events = list(exit_events.values())


    for i, event in enumerate(enter_events):
        parsing_result = add_enter_to_model(event)
        match parsing_result:
            case ParsingResult.ERR_COULD_NOT_PARSE:
                print(f"[PARSE_READ - ERROR] Could not parse event {i} properly : {event}")
                return False
            case ParsingResult.WARN_IGNORE_LINE:
                print(f"[PARSE_READ - WARNING] Ignoring event {i} : {event}")
                continue
            case ParsingResult.OK:
                continue

    for i, event in enumerate(exit_events):
        parsing_result = add_exit_to_model(event)
        match parsing_result:
            case ParsingResult.ERR_COULD_NOT_PARSE:
                print(f"[PARSE_READ - ERROR] Could not parse event {i} properly : {event}")
                return False
            case ParsingResult.WARN_IGNORE_LINE:
                print(f"[PARSE_READ - WARNING] Ignoring event {i} : {event}")
                continue
            case ParsingResult.OK:
                continue
        
    return True


def add_exit_to_model(event: tuple) -> int:
    
    if len(event) not in [N_INFOS_ENTER, N_INFOS_EXIT]:
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

    if any(name == ignore for ignore in IGNORE_PATTERN):
        return ParsingResult.WARN_IGNORE_LINE
    
    new_process = Process(pid, name)
    process = GlobalModel.add_or_get_process(new_process)

    exit_read_event = ExitReadEvent(timestamp, f"{process.name}-{process.pid} finishes reading from fd {fd}", process, fd, size, content, ret)
    GlobalModel.add_event(exit_read_event)
    
    return ParsingResult.OK


def add_enter_to_model(event: tuple) -> int:

    if len(event) not in [N_INFOS_ENTER, N_INFOS_EXIT]:
        return ParsingResult.ERR_COULD_NOT_PARSE

    (
        timestamp,
        name,
        pid,
        fd,
        size,
    ) = event

    if any(name == ignore for ignore in IGNORE_PATTERN):
        return ParsingResult.WARN_IGNORE_LINE
    
    new_process = Process(pid, name)
    process = GlobalModel.add_or_get_process(new_process)

    enter_read_event = EnterReadEvent(timestamp, f"{process.name}-{process.pid} starts reading from fd {fd}", process, fd, size)
    GlobalModel.add_event(enter_read_event)

    return ParsingResult.OK