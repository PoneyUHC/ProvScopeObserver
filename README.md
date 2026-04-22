# ProvScope Observer

ProvScope Observer is a GNU/Linux IPC tracing and analysis prototype. It runs
small inter-process C systems, traces selected system calls with `bpftrace`, and
exports a normalized JSON provenance model describing which processes interacted
with which files, FIFOs, sockets, and standard streams.

The Python package name is `provscope_observer`.

## What It Does

- Builds and launches example IPC systems written in C.
- Generates `bpftrace` programs for selected process names.
- Captures `openat`, `read`, `write`, and `close` events.
- Parses raw bpftrace output into processes, resources, and events.
- Normalizes timestamps and file-descriptor relationships.
- Exports JSON reports under `src/provscope_observer/present_result/output/`.
- Can replay scripted interactions from JSON scenario files.

## Repository Layout

```text
.
├── pyproject.toml
├── LICENSE
└── src/provscope_observer
    ├── programs/               # Router/client/log-collector demo system
    ├── router_ab_programs/      # Router + process A/process B demo system
    ├── router_users_programs/   # Router/auth/access/users demo system
    ├── evaluator_interface/     # JSON scenarios and auto_attacker.py
    ├── trace/                   # bpftrace templates and tracer launcher
    ├── present_result/          # Log parsers, normalization, JSON export
    ├── scripts/                 # Build/run orchestration scripts
    └── utils.py                 # Shared process shutdown helper
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

Run the scripted `router_users_programs` scenario:

```bash
python3 evaluator_interface/auto_attacker.py evaluator_interface/router_users_actions.json
```

This command:

1. Reads the evaluator scenario.
2. Builds and starts the configured C system.
3. Instantiates bpftrace scripts for the configured process names.
4. Starts bpftrace with `sudo`.
5. Replays each test case against the configured FIFO targets.
6. Exports one JSON report per test case.

Reports are written to:

```text
src/provscope_observer/present_result/output/<system_name>/<test_case>_0.json
```

For example:

```text
src/provscope_observer/present_result/output/router_users_programs/user_authenticates_0.json
```

## Scenario Files

Scenario files live in `src/provscope_observer/evaluator_interface/`.

Examples:

- `router_users_actions.json` runs the router/users/auth/access system.
- `evaluator_actions.json` runs the router A/B system.
- `scenario.json` runs the router/client/log-collector system.

The main fields are:

```json
{
  "system_name": "router_users_programs",
  "system_executable": "router_users_programs/run.py",
  "system_executable_args": [],
  "system_processes": ["router", "auth", "access"],
  "targets": ["router_users_programs/build/exec/run/fs/comms/fifo_comm_to_u1"],
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

### `programs/`

A router/client/log-collector system. Its runner accepts:

```bash
python3 programs/run.py <n_clients> <talk_delay_microseconds>
```

The included `scenario.json` runs this system with an empty test-case list, so
the evaluator simply starts the system, waits, traces it, and exports a report.

### `router_ab_programs/`

A small router that forwards requests to process A or process B. The
`evaluator_actions.json` file contains interactions such as `choose_target A`,
`choose_target B`, and `send_message Hello`.

### `router_users_programs/`

A router/auth/access/users system with user FIFOs, passwords, and a simple
policy file. `router_users_actions.json` includes authentication, read/write,
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
