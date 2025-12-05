
from ipc_analyzer.present_result.ipca_globals import GlobalModel, ParsingResult, Process, EnterReadEvent, ExitReadEvent
from ipc_analyzer.present_result.parse_logs.parse_globals import IGNORE_PATTERN, bpftrace_to_IPCA


N_INFOS_ENTER = 5
N_INFOS_EXIT = 7


def parse_bpf_read_logs(filename: str) -> bool:
    
    read_events = bpftrace_to_IPCA(filename, keys=["@enter_events", "@exit_events"], merge=False)

    # since merge=False, we have a list with two elements being the list of enter and exit events
    enter_events = read_events[0]
    exit_events = read_events[1]
    
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
        content,
        ret
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