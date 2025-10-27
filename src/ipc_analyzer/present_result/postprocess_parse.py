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


def normalize_timestamps():
    if not GlobalModel.events:
        return

    min_timestamp = min(event.timestamp for event in GlobalModel.events)

    for event in GlobalModel.events:
        event.timestamp -= min_timestamp


def normalize_resources():

    process_resource_map = {}

    for event in GlobalModel.events:
        if event.event_type in ['OpenEvent', 'CloseEvent']:
            process_uuid = event.process.get_uuid()
            resource_key = (process_uuid, event.fd)

            if event.event_type == 'OpenEvent':
                process_resource_map[resource_key] = event.resource
            elif event.event_type == 'CloseEvent':
                if resource_key in process_resource_map:
                    del process_resource_map[resource_key]

        elif event.event_type == 'EnterReadEvent' or event.event_type == 'ExitReadEvent' or event.event_type == 'WriteEvent':
            process_uuid = event.process.get_uuid()
            resource_key = (process_uuid, event.fd)

            if resource_key in process_resource_map:
                event.resource = process_resource_map[resource_key]