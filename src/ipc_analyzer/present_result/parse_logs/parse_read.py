
from ipc_analyzer.present_result.ipca_globals import GlobalModel, ParsingResult, Process, EnterReadEvent, ExitReadEvent
from ipc_analyzer.present_result.parse_logs.parse_globals import IGNORE_PATTERN, SPLIT_PATTERN

N_INFOS_ENTER = 6
N_INFOS_EXIT = 8

def parse_bpf_read_logs(filename: str) -> bool:
    lines = []
    with open(filename, 'r') as fin:
        lines = fin.readlines()[1:]
    
    for i, line in enumerate(lines):
        parsing_result = parse_line(line)
        match parsing_result:
            case ParsingResult.ERR_COULD_NOT_PARSE:
                print(f"[PARSE_READ - ERROR] Could not parse line {i} properly : {line}")
                return False
            case ParsingResult.WARN_IGNORE_LINE:
                print(f"[PARSE_READ - WARNING] Ignoring line {i} : {line}")
                continue
            case ParsingResult.OK:
                continue
        
    return True


def parse_line(line: str) -> int:

    parts = line.strip().split(SPLIT_PATTERN)
    if len(parts) not in [N_INFOS_ENTER, N_INFOS_EXIT]:
        return ParsingResult.ERR_COULD_NOT_PARSE

    is_exit = parts[0] == 'exit'

    timestamp = int(parts[1])
    name = parts[2]

    if any(name == ignore for ignore in IGNORE_PATTERN):
        return ParsingResult.WARN_IGNORE_LINE

    pid = int(parts[3])
    fd = int(parts[4])
    size = int(parts[5])
    
    new_process = Process(pid, name)
    process = GlobalModel.add_or_get_process(new_process)

    
    if is_exit:
        content = parts[6]
        ret = parts[7]
        event = ExitReadEvent(timestamp, f"{process.name}-{process.pid} finishes reading from fd {fd}", process, fd, size, content, ret)
    else:
        event = EnterReadEvent(timestamp, f"{process.name}-{process.pid} starts reading from fd {fd}", process, fd, size)
    
    GlobalModel.add_event(event)
    return ParsingResult.OK