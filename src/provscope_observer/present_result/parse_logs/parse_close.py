
from provscope_observer.present_result.ProvScopeGlobals import GlobalModel, Process, ParsingResult, CloseEvent
from provscope_observer.present_result.parse_logs.parse_globals import IGNORE_PATTERN, EXT_USTACKS, gather_ustacks, get_bpftrace_map


N_INFOS = 5


def parse_bpf_close_logs(filename: str) -> bool:

    close_events_arguments_by_id = get_bpftrace_map(filename, key="@close_events")
    if close_events_arguments_by_id is None:
        print(f"[PARSE_CLOSE - ERROR] Could not find @close_events map in {filename}")
        return False

    close_events_by_id = dict()
    for id, close_event_arguments in close_events_arguments_by_id.items():
        parsing_result, close_event = add_to_model(close_event_arguments)
        match parsing_result:
            case ParsingResult.ERR_COULD_NOT_PARSE:
                print(f"[PARSE_CLOSE - ERROR] Could not parse event {id} properly : {close_event_arguments}")
                return False
            case ParsingResult.WARN_IGNORE_LINE:
                print(f"[PARSE_CLOSE - WARNING] Ignoring event {id} : {close_event_arguments}")
                continue
            case ParsingResult.OK:
                close_events_by_id[id] = close_event

    if EXT_USTACKS:
        gather_ustacks(filename, close_events_by_id)


    return True



def add_to_model(event: tuple) -> int:

    if len(event) != N_INFOS:
        return ParsingResult.ERR_COULD_NOT_PARSE, None

    (
        timestamp,
        name,
        pid,
        fd,
        ret
    ) = event

    if any(name == ignore for ignore in IGNORE_PATTERN):
        return ParsingResult.WARN_IGNORE_LINE, None

    new_process = Process(pid, name)
    process = GlobalModel.add_or_get_process(new_process)
    
    close_event = CloseEvent(timestamp, f"{process.name}-{process.pid} closes fd {fd}", process, fd, ret)
    GlobalModel.add_event(close_event)

    return ParsingResult.OK, close_event