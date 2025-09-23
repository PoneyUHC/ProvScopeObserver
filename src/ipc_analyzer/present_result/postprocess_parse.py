from ipc_analyzer.present_result.ipca_globals import FileType, CommunicationChannel, CommunicationDirection, GlobalModel

def add_stdios():
    
    for event in GlobalModel.events:

        process_uuid = event.process.get_uuid()

        if event.fd == 0:
            channel_name = f"{process_uuid}-STDIN"
            channel = CommunicationChannel(channel_name, FileType.FIFO, CommunicationDirection.READ)
            GlobalModel.add_or_get_channel(channel)
        elif event.fd == 1:
            channel_name = f"{process_uuid}-STDOUT"
            channel = CommunicationChannel(channel_name, FileType.FIFO, CommunicationDirection.WRITE)
            GlobalModel.add_or_get_channel(channel)
        elif event.fd == 2:
            channel_name = f"{process_uuid}-STDERR"
            channel = CommunicationChannel(channel_name, FileType.FIFO, CommunicationDirection.WRITE)
            GlobalModel.add_or_get_channel(channel)


def sort_events():
    GlobalModel.events.sort(key=lambda event: event.timestamp)