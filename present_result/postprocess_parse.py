from ipca_globals import GlobalModel

def unify_bpf_logs():
    for process in GlobalModel.processes:
        for communication_info in process.communication_infos:
            fd = communication_info.fd
            timestamp = communication_info.timestamp

            open_info = process.get_open_info_at_time(fd, timestamp)

            if open_info is None:
                print(f"{process.pid}-{process.name}: cannot determine file for {communication_info} (opened before log started)")
                continue
            if open_info.file is None:
                print(f"{process.pid}-{process.name}: cannot determine file for {communication_info} (closed, opened before log started)")
                continue

            communication_info.channel.name = open_info.file.path
