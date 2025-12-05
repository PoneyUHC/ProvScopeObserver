
from ipc_analyzer.present_result.ipca_globals import GlobalModel, ParsingResult, Process, WriteEvent
from ipc_analyzer.present_result.parse_logs.parse_globals import IGNORE_PATTERN, bpftrace_to_IPCA


N_INFOS = 7


def parse_bpf_write_logs(filename: str) -> bool:
    
    write_events = bpftrace_to_IPCA(filename, keys=["@write_events"], merge=False)

    # since merge=False, we have a list with one element being the list of event
    write_events = write_events[0]
    
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
        content,
        ret
    ) = event

    if any(name == ignore for ignore in IGNORE_PATTERN):
        return ParsingResult.WARN_IGNORE_LINE
    
    new_process = Process(pid, name)
    process = GlobalModel.add_or_get_process(new_process)

    write_event = WriteEvent(timestamp, f"{process.name}-{process.pid} writes to fd {fd}", process, fd, size, content, ret)
    GlobalModel.add_event(write_event)

    return ParsingResult.OK