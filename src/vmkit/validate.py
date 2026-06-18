"""VM-specific input validators.

These raise `vmkit.errors.ValidationError` (a `ValueError` subclass) rather than
an argparse type, so they're reusable by any caller — CLI, REST API, or direct
library use. The CLI adapts `ValidationError` into argparse errors.

Hostname/IP/prefix validation is NOT here — those are generic networking concerns
and live in the `configgen` library.
"""

import re
from pathlib import Path

from vmkit.errors import ValidationError

MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


def validate_mac(value: str) -> str:
    if not MAC_RE.match(value):
        raise ValidationError(
            f"Invalid MAC address '{value}'. "
            "Expected format: XX:XX:XX:XX:XX:XX (e.g. 00:50:56:00:00:01)."
        )
    return value.lower()


def validate_cpus(value) -> int:
    try:
        n = int(value)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid CPU count '{value}': must be a positive integer.")
    if n < 1:
        raise ValidationError(f"Invalid CPU count '{value}': must be at least 1.")
    if n > 128:
        raise ValidationError(
            f"Invalid CPU count '{value}': ESXi supports a maximum of 128 vCPUs."
        )
    if (n & (n - 1)) != 0:
        raise ValidationError(
            f"Invalid CPU count '{value}': must be a power of 2 (1, 2, 4, 8, 16…)."
        )
    return n


def validate_memory(value) -> int:
    try:
        mb = int(value)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid memory value '{value}': must be a positive integer (MB).")
    if mb < 512:
        raise ValidationError(f"Invalid memory value '{value}': minimum is 512 MB.")
    if mb % 4 != 0:
        raise ValidationError(f"Invalid memory value '{value}': must be a multiple of 4 MB.")
    return mb


def validate_iso_path(value: str) -> str:
    path = Path(value)
    if not path.is_file():
        raise ValidationError(f"ISO file not found: '{value}'.")
    if path.suffix.lower() != ".iso":
        raise ValidationError(f"File '{value}' does not end in .iso.")
    return value
