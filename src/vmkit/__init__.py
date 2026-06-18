"""vmkit — ESXi/vCenter VM automation library.

High-level entry points (params in, exceptions out, no TTY/printing):

    from vmkit import open_connection, clone_workflow, update_workflow

Low-level building blocks live in vmkit.esxi / vmkit.datastore / vmkit.vmx.
"""

from vmkit.errors import (
    AuthenticationError,
    ConnectionFailedError,
    InsufficientSpaceError,
    ValidationError,
    VmExistsError,
    VmkitError,
    VmNotFoundError,
)
from vmkit.workflows import (
    CloneResult,
    Connection,
    UpdateResult,
    clone_workflow,
    open_connection,
    update_workflow,
)

__all__ = [
    "open_connection",
    "Connection",
    "clone_workflow",
    "update_workflow",
    "CloneResult",
    "UpdateResult",
    "VmkitError",
    "ValidationError",
    "AuthenticationError",
    "ConnectionFailedError",
    "VmExistsError",
    "VmNotFoundError",
    "InsufficientSpaceError",
]
