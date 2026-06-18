"""Typed exceptions raised by vmkit.

Library code raises these; callers (CLI, REST API) map them to exit codes / HTTP
statuses. The library never calls sys.exit, print, or getpass.
"""


class VmkitError(Exception):
    """Base class for all vmkit errors."""


class ValidationError(VmkitError, ValueError):
    """An input value failed validation."""


class AuthenticationError(VmkitError):
    """ESXi/vCenter login failed (bad username or password)."""


class ConnectionFailedError(VmkitError):
    """Could not connect to the ESXi/vCenter host."""


class VmExistsError(VmkitError):
    """A VM with the requested name already exists."""


class VmNotFoundError(VmkitError):
    """The requested VM does not exist in inventory."""


class InsufficientSpaceError(VmkitError):
    """The operation would exceed the datastore free-space limit."""
