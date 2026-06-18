import argparse
import re
from pathlib import Path

MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
VMWARE_STATIC_OUI = "00:50:56"

_LABEL_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$")


def validate_mac(value: str) -> str:
    if not MAC_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"Invalid MAC address '{value}'. "
            "Expected format: XX:XX:XX:XX:XX:XX (e.g. 00:50:56:00:00:01)."
        )
    return value.lower()


def validate_cpus(value: str) -> int:
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid CPU count '{value}': must be a positive integer."
        )
    if n < 1:
        raise argparse.ArgumentTypeError(
            f"Invalid CPU count '{value}': must be at least 1."
        )
    if n > 128:
        raise argparse.ArgumentTypeError(
            f"Invalid CPU count '{value}': ESXi supports a maximum of 128 vCPUs."
        )
    if (n & (n - 1)) != 0:
        raise argparse.ArgumentTypeError(
            f"Invalid CPU count '{value}': must be a power of 2 (1, 2, 4, 8, 16…)."
        )
    return n


def validate_memory(value: str) -> int:
    try:
        mb = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid memory value '{value}': must be a positive integer (MB)."
        )
    if mb < 512:
        raise argparse.ArgumentTypeError(
            f"Invalid memory value '{value}': minimum is 512 MB."
        )
    if mb % 4 != 0:
        raise argparse.ArgumentTypeError(
            f"Invalid memory value '{value}': must be a multiple of 4 MB."
        )
    return mb


def validate_hostname_rfc(value: str) -> str:
    """RFC 952/1123: labels ≤63 chars, total ≤253, alphanumeric+hyphens, no leading/trailing hyphen, no underscore."""
    if len(value) > 253:
        raise argparse.ArgumentTypeError(
            f"Hostname too long ({len(value)} chars, max 253)."
        )
    for label in value.split("."):
        if not label:
            raise argparse.ArgumentTypeError(
                f"Hostname '{value}' contains an empty label."
            )
        if len(label) > 63:
            raise argparse.ArgumentTypeError(
                f"Hostname label '{label}' exceeds 63 characters."
            )
        if not _LABEL_RE.match(label):
            raise argparse.ArgumentTypeError(
                f"Hostname label '{label}' is invalid: alphanumeric and hyphens only, "
                "no leading/trailing hyphen, no underscore."
            )
    return value


def validate_iso_path(value: str) -> str:
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"ISO file not found: '{value}'.")
    if path.suffix.lower() != ".iso":
        raise argparse.ArgumentTypeError(f"File '{value}' does not end in .iso.")
    return value
