from ipca_globals import GlobalModel, ParsingResult, Process, CommunicationChannel, ChannelType, CommunicationDirection, CommunicationInfo, ReadEvent
from parse_logs.parse_globals import IGNORE_PATTERN, SPLIT_PATTERN

N_INFOS = 6

def parse_bpf_read_logs(filename: str) -> bool:
    lines = []
    with open(filename, 'r') as fin:
        lines = fin.readlines()[1:]
    
    for i, line in enumerate(lines):
        parsing_result = parse_line(line)
        match parsing_result:
            case ParsingResult.ERR_COULD_NOT_PARSE:
                print(f"Could not parse line {i} properly : {line}")
                return False
            case ParsingResult.WARN_IGNORE_LINE:
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
    fd = int(parts[3])
    size = int(parts[4])
    content = parts[5]
    
    new_process = Process(pid, name)
    process = GlobalModel.add_or_get_process(new_process)
    
    channel = CommunicationChannel("Unknown", ChannelType.FIFO)
    GlobalModel.add_channel(channel)

    communication_info = CommunicationInfo(timestamp, channel, fd, CommunicationDirection.READ, size, content)
    process.add_communication_info(communication_info)
    
    event = ReadEvent(timestamp, f"{process.name}-{process.pid} reads from fd {fd}", process, fd, size, content)
    GlobalModel.add_event(event)

    return ParsingResult.OK