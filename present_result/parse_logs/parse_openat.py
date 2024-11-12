
from ipca_globals import GlobalModel, Process, File, OpenInfo

remove_pattern = ['\n', 'sleep', 'run.bash']
split_pattern = "---"

def parse_bpf_openat_logs(filename: str) -> bool:
    lines = []
    with open(filename, 'r') as fin:
        lines = fin.readlines()[1:]
    
    for i, line in enumerate(lines):
        if any(line.startswith(pattern) for pattern in remove_pattern):
            continue

        if not parse_line(line):
            print(f"Could not parse line {i} properly : {line}")
            return False
        
    return True


def parse_line(line: str) -> bool:

    parts = line.strip().split(split_pattern)
    if len(parts) != 6:
        return False

    print(parts)
    name = parts[0]
    pid = int(parts[1])
    path = parts[2]
    fd = int(parts[3])
    mode = int(parts[4])
    flags = int(parts[5])
    
    new_process = Process(pid, name)
    process = GlobalModel.add_or_get_process(new_process)
    
    new_file = File(path, None)
    file = GlobalModel.add_or_get_file(new_file)

    open_info = OpenInfo(file, fd, mode, flags)
    process.open_file(open_info)


    return True