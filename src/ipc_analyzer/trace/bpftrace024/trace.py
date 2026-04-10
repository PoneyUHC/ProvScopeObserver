import subprocess
import time
from pathlib import Path

from ipc_analyzer.utils import EndProcessWatcher

TRACE_NAMES = ("open", "close", "write", "read")


def get_run_dirs() -> tuple[Path, Path]:
    backend_dir = Path(__file__).resolve().parent
    run_dir = backend_dir.parent / "run" / backend_dir.name
    return run_dir / "scripts", run_dir / "logs"


def start():
    procs = []
    scripts_dir, logs_dir = get_run_dirs()

    logs_dir.mkdir(parents=True, exist_ok=True)

    for trace_name in TRACE_NAMES:
        script_path = scripts_dir / f"trace_{trace_name}.bt"
        log_path = logs_dir / f"trace_{trace_name}.logs"

        with log_path.open("w") as fout:
            proc = subprocess.Popen(
                ["sudo", "bpftrace", "-f", "json", str(script_path)],
                stdout=fout,
            )
            procs.append(proc)

    return procs


def clean(procs: list[subprocess.Popen]):
    for p in procs:
        subprocess.run(["sudo", "kill", "-INT", f"{p.pid}"])


def main() -> None:
    watcher = EndProcessWatcher()
    procs = start()

    while not watcher.kill_now:
        time.sleep(0.2)

    clean(procs)


if __name__ == "__main__":
    main()
