# Evaluator interface — README

This directory contains small evaluator helper files and a script (`auto_attacker.py`) used to exercise the example IPC systems (e.g. router, auth, access, users) with scripted interactions.

Locations
- Test scenarios (example): `src/provscope_observer/evaluator_interface/scenarios/composition_scenario.json`
- Driver script: `src/provscope_observer/evaluator_interface/auto_attacker.py`
- Helper runner scripts (used by the project): `src/provscope_observer/scripts/run.bash` (invoked by the auto-attacker for each test case)

Purpose
- Provide human-readable test cases that the `auto_attacker.py` can convert to raw bytes and write to the appropriate FIFOs or `request` targets.
- Make it easy to express both plain-text interactions and binary payloads (using `\xNN` escapes) in JSON.

Payload formats supported
`auto_attacker.py` accepts payloads in several forms. The parser will turn any of these into raw bytes before sending:

1. Plain text (human readable)
   - Example: `"AUTH 1 secretpass\n"`
   - Newline sequences (`\n`) are interpreted as a single byte 0x0A.

2. C-style escaped text (use this when you need non-printable bytes)
   - Example: `"WRITE 1 /tmp/user1/binfile \\x00\\x01\\x02\\n"` in JSON (double-escaped in JSON):
     - When read by Python JSON loader this becomes `"WRITE 1 /tmp/user1/binfile \x00\x01\x02\n"`.
     - The parser decodes `\xNN` and other C-style escapes using Python's `unicode_escape`, then encodes to `latin-1` to produce the expected raw bytes.
   - Use this when you need embedded NUL bytes or other control codes.

3. Continuous hex string
   - Example: `"6368616e67656d652e0a"` (equivalent to `"changeme.\n"`)
   - The parser detects hex-like strings (optionally with dot/underscore separators) and decodes them directly.

4. Dotted or underscored hex (legacy)
   - Example: `"63.68.61.6e.67.65.6d.65.0a"` or `"63_68_61_6e"`
   - Still accepted for backward compatibility.

How the JSON should look
- JSON uses an array of `test_cases`.
- Each test case has a `name` and `interactions` array.
- Each `interaction` contains `target_index` (index into the `targets` array) and `payload` (one of the formats above).

Example snippet (human-readable):

```json
{
  "name": "auth_user1_success",
  "interactions": [
    { "target_index": 0, "payload": "AUTH 1 secretpass\n" }
  ]
}
```

Note about escaping in JSON files
- To include literal `\x` sequences in JSON you must escape the backslash. In the file that means writing `\\x00` in the JSON source so that after JSON decoding the Python string contains `\x00` which the parser then decodes into a NUL byte.

How to run
- Quick syntax check for the driver script:

```bash
python3 -m py_compile src/provscope_observer/evaluator_interface/auto_attacker.py
```

- Run the auto-attacker using a scenario file (example):

```bash
python3 src/provscope_observer/evaluator_interface/auto_attacker.py src/provscope_observer/evaluator_interface/scenarios/composition_scenario.json
```

Notes about `run.bash` invocation
- For each test case, `auto_attacker.py` creates a small temporary bash script that writes base64-decoded payloads into the configured `targets` (this avoids quoting issues). That temporary script is then passed to `scripts/run.bash`, which builds and starts the system, instantiates and starts the bpftrace tracers, runs the temporary script to feed input at the right time, and exports the resulting report.

Troubleshooting and tips
- If a payload doesn't look right in the target program's logs, inspect the decoded bytes by adding a debug test case that writes hex payloads and log the bytes in the receiving program.
- If you need many binary test vectors, consider writing them as continuous hex strings — they're compact and safe in JSON.
