
from ipc_analyzer.present_result.ipca_globals import GlobalModel, Process, ParsingResult, CloseEvent
from ipc_analyzer.present_result.parse_logs.parse_globals import IGNORE_PATTERN, bpftrace_to_IPCA


N_INFOS = 5


def parse_bpf_close_logs(filename: str) -> bool:

    close_events = bpftrace_to_IPCA(filename, keys=["@close_events"], merge=False)
    if not close_events:
        return False
    
    # since merge=False, we have a list with one element being the list of event
    close_events = close_events[0] 
    
    for i, event in enumerate(close_events):
        parsing_result = add_to_model(event)
        match parsing_result:
            case ParsingResult.ERR_COULD_NOT_PARSE:
                print(f"[PARSE_CLOSE - ERROR] Could not parse event {i} properly : {event}")
                return False
            case ParsingResult.WARN_IGNORE_LINE:
                print(f"[PARSE_CLOSE - WARNING] Ignoring event {i} : {event}")
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
        ret
    ) = event

    if any(name == ignore for ignore in IGNORE_PATTERN):
        return ParsingResult.WARN_IGNORE_LINE
    
    new_process = Process(pid, name)
    process = GlobalModel.add_or_get_process(new_process)
    
    close_event = CloseEvent(timestamp, f"{process.name}-{process.pid} closes fd {fd}", process, fd, ret)
    GlobalModel.add_event(close_event)

    return ParsingResult.OK