"""Importing this package registers every check, in the order they run."""

from . import service, ports, wol, lock, dns, tailscale  # noqa: F401
