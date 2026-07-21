<img width="640" height="200" alt="provscope-observer-logo" src="https://github.com/user-attachments/assets/3e09dc9a-f9cb-4d0c-820b-dd976fccdc4e" />


# ProvScope Observer

ProvScope Observer is a GNU/Linux IPC tracing and analysis prototype. It runs
small inter-process C systems, traces selected system calls with `bpftrace`, and
exports a normalized JSON provenance model describing which processes interacted
with which files, FIFOs, sockets, and standard streams. It is aimed to be used with 
[ProvScope App](https://github.com/PoneyUHC/ProvScopeApp)

The Python package name is `provscope_observer`.

## What It Does

- Builds and launches example IPC systems written in C.
- Generates `bpftrace` programs for selected process names.
- Captures `openat`, `read`, `write`, and `close` events, with their respective user stacks.
- Parses raw bpftrace output into processes, resources, and events.
- Normalizes timestamps and file-descriptor relationships.
- Exports JSON reports under `src/provscope_observer/trace_export/output/`.
- Can replay scripted interactions from JSON scenario files.

## Repository Layout

```text
.
├── pyproject.toml
├── LICENSE
└── src/provscope_observer
    ├── systems/                        # Example IPC systems written in C
    │   ├── communication_system/       # Router/client/log-collector demo system
    │   └── composition_system/         # Router/auth/access/users demo system
    ├── evaluator_interface/            # Scenarios and auto_attacker.py
    │   └── scenarios/                  # JSON scenario files
    ├── tracers/                        # bpftrace templates and tracer launcher
    ├── trace_export/                   # Log parsers, normalization, JSON export
    ├── scripts/                        # Build/run orchestration scripts
    └── utils.py                        # Shared process shutdown helper
```

Generated build products, logs, trace scripts, run directories, and output
reports are ignored by Git.

## Requirements

- GNU/Linux with eBPF/bpftrace support.
- Python 3.12 or newer.
- `gcc`, `make`, `bash`, `jq`, `base64`, and `sudo`.
- `bpftrace` installed and allowed to attach to kernel tracepoints/kprobes.

On Debian/Ubuntu-like systems, the system packages are typically similar to:

```bash
sudo apt install python3 python3-venv gcc make jq bpftrace
```

## Installation

From the repository root:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

The editable install makes `provscope_observer` importable while you work on the
source tree.

## Quick Start

Most runner scripts expect the current working directory to be the package
directory:

```bash
cd src/provscope_observer
```

Run the scripted `composition_system` scenario:

```bash
python3 evaluator_interface/auto_attacker.py evaluator_interface/scenarios/composition_scenario.json
```

This command:

1. Reads the evaluator scenario.
2. Builds a small bash script per test case that writes the configured payloads to
   the target FIFOs.
3. For each test case, calls `scripts/run.bash`, which:
   - Instantiates bpftrace scripts for the configured process names.
   - Starts bpftrace with `sudo`.
   - Starts the configured C system.
   - Replays the test case's interactions against the FIFO targets.
   - Waits, stops tracing, and exports one JSON report.

Reports are written to:

```text
src/provscope_observer/trace_export/output/<system_name>/<test_case>_0.json
```

For example:

```text
src/provscope_observer/trace_export/output/composition_system/user_authenticates_0.json
```

## Scenario Files

Scenario files live in `src/provscope_observer/evaluator_interface/scenarios/`.

Examples:

- `composition_scenario.json` runs the router/auth/access/users system
  (`systems/composition_system/`).
- `communication_scenario.json` runs the router/client/log-collector system
  (`systems/communication_system/`) with an empty test-case list.

The main fields are:

```json
{
  "system_name": "composition_system",
  "system_executable": "systems/composition_system/run.py",
  "system_executable_args": [],
  "system_processes": ["router", "auth", "access"],
  "targets": ["systems/composition_system/build/exec/run/fs/comms/fifo_comm_to_u1"],
  "test_cases": [
    {
      "name": "user_authenticates",
      "interactions": [
        { "target_index": 0, "payload": "AUTH user1_is_da_best\n" }
      ]
    }
  ]
}
```

`system_processes` is passed to the trace template generator and should match the
Linux `comm` names that bpftrace sees for the processes you want to trace.

Payloads may be plain text, escaped text such as `\n` or `\x00`, continuous hex,
or dotted/underscored hex. See
`src/provscope_observer/evaluator_interface/README.md` for more detail.

## Example Systems

### `systems/communication_system/`

A router/client/log-collector system. Its runner accepts:

```bash
python3 systems/communication_system/run.py <n_clients> <talk_delay_microseconds>
```

The included `communication_scenario.json` runs this system with an empty
test-case list, so the evaluator simply starts the system, waits, traces it,
and exports a report.

### `systems/composition_system/`

A router/auth/access/users system with user FIFOs, passwords, and a simple
policy file. `composition_scenario.json` includes authentication, read/write,
malformed-message, and denied-access scenarios.

## Output Model

Exported reports are JSON objects with:

- `processes`: traced process identities.
- `resources`: files, FIFOs, sockets, directories, and standard streams.
- `events`: normalized events with source and target entity references.
- `_extensions`: extra visualization metadata, currently event colors.

`EnterReadEvent` records are used during parsing and filtered out before export.

## License

This repository is licensed under the terms in `LICENSE`.
