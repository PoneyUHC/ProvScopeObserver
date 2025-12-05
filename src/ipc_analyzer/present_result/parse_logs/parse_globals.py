IGNORE_PATTERN = ['sleep', 'exec.bash', 'sudo', 'python3', 'DEBUG']
SPLIT_PATTERN = "---"

def file_to_JSON_objects(filename: str) -> list[dict]:
    import json

    decoder = json.JSONDecoder()
    objs = []

    with open(filename) as f:
        txt = f.read()

    i = 0
    while i < len(txt):
        obj, idx = decoder.raw_decode(txt, i)
        objs.append(obj)
        i = idx
        # skip whitespace between objects
        while i < len(txt) and txt[i].isspace():
            i += 1

    return objs


def bpftrace_to_IPCA(filename: str, keys: list[str], merge: bool) -> list[dict]:

    ipca_events = []

    json_objs = file_to_JSON_objects(filename)
    # collect enter/exit maps from the multiple JSON objects
    partial_maps = [{} for _ in range(len(keys))]
    for i, obj in enumerate(json_objs):
        data = obj.get("data", {})
        for k in keys:
            if k in data:
                partial_maps[i] = data[k]


    for partial_map in partial_maps:
        arr = [v for _, v in partial_map.items()]
        ipca_events.append(arr)

    if merge:
        merged_events = []
        for event in zip(*ipca_events):
            new_event = []
            for argument in event:
                if isinstance(argument, list):
                    new_event.extend(argument)
                else:
                    new_event.append(argument)
            merged_events.append(new_event)
        ipca_events = merged_events

    return ipca_events