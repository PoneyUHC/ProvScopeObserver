from provscope_observer.present_result.ProvScopeGlobals import Event, GlobalModel


IGNORE_PATTERN = ['sleep', 'exec.bash', 'sudo', 'python3', 'DEBUG']
EXT_USTACKS = True


def gather_ustacks(filename: str, events_by_id: dict[str, Event]) -> None:
    ustacks_by_id = get_bpftrace_map(filename, key="@ustacks")
    if ustacks_by_id is None:
        print(f"[PARSE_GLOBALS - ERROR] Could not find @ustacks map in {filename}")
        return
    for id, event in events_by_id.items():
        if id not in ustacks_by_id.keys():
            print(f"[PARSE_GLOBALS - WARNING] Found user stack with id {id} but no corresponding event. Ignoring.")
            continue

        ustack = ustacks_by_id[id]
        GlobalModel.ext_ustacks[event] = ustack


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


def bpftrace_buffer_to_bytestring(buffer: list[int]) -> str:
    return "".join("{:02x}".format(byte) for byte in buffer)


def bpftrace_bufstr_to_bytestring(buffer: str) -> str:
    # bpftrace buf() emits printable bytes as-is and non-printable ones as \xNN.
    # After JSON decoding, we receive a normal Python str where \xNN appears as
    # the 4-char literal sequence: backslash, 'x', hex, hex.
    out = []
    i = 0
    n = len(buffer)
    while i < n:
        c = buffer[i]
        if c == "\\" and i + 3 < n and buffer[i + 1] == "x":
            out.append(buffer[i + 2:i + 4].lower())
            i += 4
        else:
            out.append("{:02x}".format(ord(c)))
            i += 1
    return "".join(out)
