# Communication system (C launcher)

Same system as `communication_system`, with the Python entry point (`run.py`) ported to C
(`src/run.c`, built as `run.bin`).

## Build

```bash
make            # system processes + launcher
make system     # system processes only (the ones the launcher starts)
make launcher   # launcher only
make cross      # everything, cross-compiled for the target, under cross/
```

`make cross` re-runs `make all` with `CROSS_CC`/`CROSS_CFLAGS` and its own build
directory, so host and target objects never mix. The `cross/` tree keeps the layout
the launcher expects (`cross/run.bin` next to `cross/build/exec/`), and both
compilers are set at the top of the `Makefile`.

`run.bin` is built at the root of this folder, next to the `tracer` it has to run.

## Run

```bash
./run.bin [n_targets] [talk_delay_ms]
```

The launcher builds nothing : it expects the system processes to be already built.
It moves to `build/exec`, starts every process, then waits for `SIGINT`/`SIGTERM`
to terminate them all. It stops with an explicit message if one of the binaries is
missing there.

## Tracer

Unlike `run.py`, which redirected the standard output of each process to
`run/[process_name].logs`, the launcher starts every process through a `tracer`
executable expected in this directory:

```
./tracer -o run/[process_name].logs [process_to_execute] [process arguments]*
```

The `-o` file keeps the log names used by `run.py`: `router.logs`, `client[i].logs`
and `log_c.logs`. The launcher aborts with an explicit message if no executable
`tracer` is found next to it, and the pids it tracks (and terminates on exit) are
those of the tracers.
