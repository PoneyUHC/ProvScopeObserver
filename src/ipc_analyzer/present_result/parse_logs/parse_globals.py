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


def get_bpftrace_map(filename: str, key: str) -> dict | None:

    json_objs = file_to_JSON_objects(filename)

    for obj in json_objs:
        data = obj.get("data", {})
        if key in data:
            return data[key]
        
    return None
