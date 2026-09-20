"""Importing this package registers every check, in the order they run."""

from . import service, ports, wol, dns, tailscale  # noqa: F401
