"""Importing this package registers every check, in the order they run."""

from . import service, ports, wol, tailscale  # noqa: F401
