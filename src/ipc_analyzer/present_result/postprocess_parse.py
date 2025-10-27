from ipc_analyzer.present_result.ipca_globals import Resource, ResourceType, GlobalModel

def add_stdios():
    
    for event in GlobalModel.events:

        process_uuid = event.process.get_uuid()

        if event.fd == 0:
            resource_name = f"{process_uuid}-STDIN"
            resource = Resource(resource_name, ResourceType.FIFO)
            GlobalModel.add_or_get_resource(resource)
        elif event.fd == 1:
            resource_name = f"{process_uuid}-STDOUT"
            resource = Resource(resource_name, ResourceType.FIFO)
            GlobalModel.add_or_get_resource(resource)
        elif event.fd == 2:
            resource_name = f"{process_uuid}-STDERR"
            resource = Resource(resource_name, ResourceType.FIFO)
            GlobalModel.add_or_get_resource(resource)


def sort_events():
    GlobalModel.events.sort(key=lambda event: event.timestamp)