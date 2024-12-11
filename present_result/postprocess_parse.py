from ipca_globals import GlobalModel

def unify_bpf_logs():
    for process in GlobalModel.processes:
        for communication_info in process.communication_infos:
            fd = communication_info.fd

            if fd == 0:
                communication_info.channel.name = f"{process.name}-{process.pid}-STDIN"
                continue
            elif fd == 1:
                communication_info.channel.name = f"{process.name}-{process.pid}-STDOUT"
                continue
            elif fd == 2:
                communication_info.channel.name = f"{process.name}-{process.pid}-STDERR"
                continue

            timestamp = communication_info.timestamp

            open_info = process.get_open_info_at_time(fd, timestamp)

            if open_info is None:
                print(f"{process.pid}-{process.name}: cannot determine file for {communication_info} (opened before log started)")
                continue
            if open_info.file is None:
                print(f"{process.pid}-{process.name}: cannot determine file for {communication_info} (closed, opened before log started)")
                continue

            communication_info.channel.name = open_info.file.path

    
    # remove duplicate channels
    new_channels = []
    for process in GlobalModel.processes:
        for communication_info in process.communication_infos:
            channel = communication_info.channel
            if channel in new_channels:
                communication_info.channel = new_channels[new_channels.index(channel)]
            else:
                new_channels.append(channel)
            
    GlobalModel.channels = new_channels


    # patch stdin / stdout infos to retrieve the correct files (at bpftrace time)
    # TODO
    
    
def sort_events():
    GlobalModel.events.sort(key=lambda event: event.timestamp)