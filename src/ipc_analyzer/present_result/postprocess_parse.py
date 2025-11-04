
import os
from ipc_analyzer.present_result.ipca_globals import CloseEvent, EnterReadEvent, ExitReadEvent, OpenEvent, Resource, ResourceType, GlobalModel, WriteEvent


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

    __add_fake_stdio_events()


def __add_fake_stdio_events():
    for process in GlobalModel.processes:
        process_uuid = process.get_uuid()

        for fd, stdio_name, stdio_type in [(0, "STDIN", ResourceType.FIFO), (1, "STDOUT", ResourceType.FIFO), (2, "STDERR", ResourceType.FIFO)]:
            resource_name = f"{process_uuid}-{stdio_name}"
            resource = Resource(resource_name, stdio_type)
            resource = GlobalModel.add_or_get_resource(resource)

            open_event = OpenEvent(-1, f"{process.name}-{process.pid} opens {stdio_name}", process, resource, fd, 0o666, os.O_RDWR)
            GlobalModel.events.insert(0, open_event)


def sort_events():
    GlobalModel.events.sort(key=lambda event: event.timestamp)


def normalize_timestamps():
    if not GlobalModel.events:
        return

    min_timestamp = min(event.timestamp for event in GlobalModel.events)

    for event in GlobalModel.events:
        event.timestamp -= min_timestamp


def normalize_events():

    process_resource_map = {}

    for event in GlobalModel.events:
        match event.event_type:
            case 'OpenEvent':
                __normalize_open(process_resource_map, event)
            case 'CloseEvent':
                __normalize_close(process_resource_map, event)
            case 'EnterReadEvent' | 'ExitReadEvent':
                __normalize_read(process_resource_map, event)
            case 'WriteEvent':
                __normalize_write(process_resource_map, event)
            case _:
                print(f"[NORMALIZE_EVENTS - WARNING] Unknown event type {event.event_type} for event {event}")
            

def __normalize_open(process_resource_map: dict[tuple[str, int], Resource], event: OpenEvent):
    process_uuid = event.process.get_uuid()
    resource_key = (process_uuid, event.fd)
    process_resource_map[resource_key] = event.file

    event.other_entities.append(event.file)
    event.source_entities.append(event.file)

    # TODO: determine in the monitoring if the file did already exist or not
    if event.flags & (os.O_TRUNC | os.O_CREAT):
        event.target_entities.append(event.file)


def __normalize_close(process_resource_map: dict[tuple[str, int], Resource], event: CloseEvent):
    process_uuid = event.process.get_uuid()
    resource_key = (process_uuid, event.fd)

    if resource_key in process_resource_map:
        del process_resource_map[resource_key]
    else: 
        print(f"[NORMALIZE_CLOSE - WARNING] Could not close fd {event.fd} for process {process_uuid} as it was not found in the map")



def __normalize_read(process_resource_map: dict[tuple[str, int], Resource], event: EnterReadEvent | ExitReadEvent):
    process_uuid = event.process.get_uuid()
    resource_key = (process_uuid, event.fd)

    if not (resource_key in process_resource_map):
        print(f"[NORMALIZE_READ - WARNING] Could not find resource for process {process_uuid} and fd {event.fd} in event {event}")
        return
    
    resource = process_resource_map[resource_key]
    event.other_entities.append(resource)

    event.source_entities.append(resource)

    if resource.resource_type in [ResourceType.FIFO, ResourceType.SOCKET]:
        event.target_entities.append(resource)


def __normalize_write(process_resource_map: dict[tuple[str, int], Resource], event: WriteEvent):
    process_uuid = event.process.get_uuid()
    resource_key = (process_uuid, event.fd)

    if not (resource_key in process_resource_map):
        print(f"[NORMALIZE_WRITE - WARNING] Could not find resource for process {process_uuid} and fd {event.fd} in event {event}")
        return
    
    resource = process_resource_map[resource_key]
    event.other_entities.append(resource)
    event.source_entities.append(resource)
    event.target_entities.append(resource)

