from ipc_analyzer.present_result.ipca_globals import GlobalModel

def add_stdios():
    
    for event in GlobalModel.events:

        process_uuid = event.process.get_uuid()

        if event.fd == 0:
            channel_name = f"{process_uuid}-STDIN"
            GlobalModel.add_or_get_channel(channel_name)
        elif event.fd == 1:
            channel_name = f"{process_uuid}-STDOUT"
            GlobalModel.add_or_get_channel(channel_name)
        elif event.fd == 2:
            channel_name = f"{process_uuid}-STDERR"
            GlobalModel.add_or_get_channel(channel_name)
    
    
def sort_events():
    GlobalModel.events.sort(key=lambda event: event.timestamp)