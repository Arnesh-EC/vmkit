"""UI-agnostic progress reporting.

The library never paints a terminal or pushes to a socket itself. Long-running
operations emit structured :class:`ProgressEvent`s through an optional
``progress`` callback that the caller threads in. The caller decides how to
render them:

    * CLI script  -> a callback that drives your own progress bar
    * web server  -> a callback that pushes each event onto a websocket / queue
    * nothing     -> pass ``None`` (the default); events are dropped, no TTY

A callback (rather than an async generator) keeps the synchronous pyVmomi code
synchronous and works for every front-end without forcing async on callers.
"""

import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable

log = logging.getLogger("deploy-vm")


class Phase(str, Enum):
    """Lifecycle of a single tracked operation."""

    START = "start"
    UPDATE = "update"
    END = "end"
    ERROR = "error"


@dataclass(frozen=True)
class ProgressEvent:
    """One progress sample for a single operation.

    ``key`` is a stable id for the operation (e.g. ``"upload:web.vmx"`` or
    ``"vmdk-copy"``) so a consumer can keep one bar / one websocket channel per
    concurrent operation. ``completed``/``total`` are in ``unit`` (``"%"`` for
    vSphere tasks, ``"B"`` for byte transfers).
    """

    key: str
    label: str
    completed: float
    total: float
    unit: str = "%"
    phase: Phase = Phase.UPDATE
    error: str | None = None

    @property
    def fraction(self) -> float:
        return (self.completed / self.total) if self.total else 0.0

    @property
    def percent(self) -> float:
        return self.fraction * 100.0


#: A progress sink. Receives every :class:`ProgressEvent`; must not raise.
ProgressCallback = Callable[[ProgressEvent], None]


class Reporter:
    """Internal helper the library uses to emit events.

    Centralises the ``None``-callback check and absolute/relative bookkeeping so
    call sites stay terse. Callers of the public API never construct one — they
    just pass a :data:`ProgressCallback`.
    """

    def __init__(
        self,
        callback: ProgressCallback | None,
        key: str,
        label: str,
        total: float,
        unit: str = "%",
    ) -> None:
        self._cb = callback
        self.key = key
        self.label = label
        self.total = total
        self.unit = unit
        self.completed = 0.0

    def start(self) -> None:
        self._emit(Phase.START)

    def advance(self, by: float) -> None:
        self.completed += by
        self._emit(Phase.UPDATE)

    def to(self, completed: float) -> None:
        if completed > self.completed:
            self.completed = completed
            self._emit(Phase.UPDATE)

    def finish(self) -> None:
        self.completed = self.total
        self._emit(Phase.END)

    def fail(self, error: str) -> None:
        self._emit(Phase.ERROR, error)

    def _emit(self, phase: Phase, error: str | None = None) -> None:
        if self._cb is None:
            return
        self._cb(
            ProgressEvent(
                key=self.key,
                label=self.label,
                completed=self.completed,
                total=self.total,
                unit=self.unit,
                phase=phase,
                error=error,
            )
        )


def human_bytes(n: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PiB"


def setup_logging(name: str, verbose: bool) -> str:
    """Configure console + timestamped file logging. Returns the log file path."""
    log.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG if verbose else logging.INFO)
    ch.setFormatter(fmt)
    log.addHandler(ch)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    logfile = Path("logs") / f"deploy_{name}_{stamp}.log"
    logfile.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(logfile, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    log.addHandler(fh)

    log.debug("Logging initialised. Log file: %s", logfile)
    return str(logfile)
