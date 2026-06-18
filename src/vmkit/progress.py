import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from tqdm import tqdm

log = logging.getLogger("deploy-vm")


def make_progress_bar(
    total: float, desc: str, unit: str = "%", unit_scale: bool = False
) -> "tqdm[Any]":
    return tqdm(
        total=total,
        desc=desc,
        unit=unit,
        unit_scale=unit_scale,
        leave=False,
        file=sys.stdout,
        dynamic_ncols=True,
        disable=None,
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
