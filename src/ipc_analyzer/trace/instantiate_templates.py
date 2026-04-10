import os
import sys
from pathlib import Path

DEFAULT_TRACE_BACKEND = "bpftrace024"


def resolve_backend_script(script_name: str, backend: str) -> Path:
    trace_root = Path(__file__).resolve().parent
    backend_script = trace_root / backend / script_name

    if backend_script.exists():
        return backend_script

    available_backends = sorted(
        path.name
        for path in trace_root.iterdir()
        if path.is_dir() and (path / script_name).exists()
    )
    available = ", ".join(available_backends) or DEFAULT_TRACE_BACKEND
    raise SystemExit(
        f"Unknown trace backend '{backend}'. Available backends: {available}"
    )


def main() -> None:
    if len(sys.argv) > 2:
        backend = sys.argv[1]
        forwarded_args = sys.argv[2:]
    else:
        backend = DEFAULT_TRACE_BACKEND
        forwarded_args = sys.argv[1:]

    backend_script = resolve_backend_script(Path(__file__).name, backend)
    os.execv(sys.executable, [sys.executable, str(backend_script), *forwarded_args])


if __name__ == "__main__":
    main()
