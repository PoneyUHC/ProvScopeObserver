

from ipc_analyzer.present_result.ipca_globals import GlobalModel, Process, File, ParsingResult, OpenEvent, FileType
from ipc_analyzer.present_result.parse_logs.parse_globals import IGNORE_PATTERN, SPLIT_PATTERN


N_INFOS = 8


def parse_bpf_openat_logs(filename: str) -> bool:
    lines = []
    with open(filename, 'r') as fin:
        lines = fin.readlines()[1:]
    
    for i, line in enumerate(lines):
        parsing_result = parse_line(line)
        match parsing_result:
            case ParsingResult.ERR_COULD_NOT_PARSE:
                print(f"[PARSE_OPEN - ERROR] Could not parse line {i} properly : {line}")
                return False
            case ParsingResult.WARN_IGNORE_LINE:
                print(f"[PARSE_OPEN - WARNING] Ignoring line {i} : {line}")
                continue
            case ParsingResult.OK:
                continue
        
    return True


def parse_line(line: str) -> int:

    parts = line.strip().split(SPLIT_PATTERN)
    if len(parts) != N_INFOS:
        return ParsingResult.ERR_COULD_NOT_PARSE

    timestamp = int(parts[0])
    name = parts[1]

    if any(name == ignore for ignore in IGNORE_PATTERN):
        return ParsingResult.WARN_IGNORE_LINE

    pid = int(parts[2])
    path = parts[3]
    fd = int(parts[4])
    mode = int(parts[5])
    flags = int(parts[6])
    file_type = int(parts[7], 8)
    
    new_process = Process(pid, name)
    process = GlobalModel.add_or_get_process(new_process)
    
    new_file = File(path, FileType.from_octal(file_type))
    file = GlobalModel.add_or_get_file(new_file)
    
    event = OpenEvent(timestamp, f"{process.name}-{process.pid} opens {file.path} with fd {fd}", process, file, fd, mode, flags)
    GlobalModel.add_event(event)

    return ParsingResult.OK