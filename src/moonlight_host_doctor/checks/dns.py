"""Are systemd-resolved and NetworkManager wired together consistently?

The common broken state: NetworkManager is set to hand DNS to systemd-resolved, but
/etc/resolv.conf is a leftover plain file instead of a link to resolved's stub file.
Lookups still work because the leftover file points at the same stub address, but
Tailscale reports it and MagicDNS can break later. Only a mismatch is reported: a
resolv.conf managed by something else on purpose is left alone.
"""

from __future__ import annotations

import re

from ..model import Result, Status, check
from ..system import System

ID = "dns"
TITLE = "DNS resolver setup"
STUB = "/run/systemd/resolve/stub-resolv.conf"
NM_DNS = [
    "busctl", "get-property", "org.freedesktop.NetworkManager",
    "/org/freedesktop/NetworkManager/DnsManager",
    "org.freedesktop.NetworkManager.DnsManager", "Mode", "RcManager",
]


def parse_resolv_conf_mode(text: str) -> str | None:
    """The 'resolv.conf mode' line of `resolvectl status`: stub, foreign, missing, ..."""
    match = re.search(r"resolv\.conf mode:\s*(\S+)", text)
    return match.group(1) if match else None


def parse_nm_dns_mode(text: str) -> str | None:
    """NetworkManager's live DNS mode: the first quoted value of the busctl output."""
    match = re.search(r'^s\s+"([^"]*)"', text, re.MULTILINE)
    return match.group(1) if match else None


def _fix(system: System) -> tuple[str, ...]:
    steps = [f"sudo ln -sf {STUB} /etc/resolv.conf"]
    if system.has_command("tailscale"):
        # Tailscale only re-reads the DNS setup when it starts.
        steps.append("sudo systemctl restart tailscaled")
    return tuple(steps)


@check(ID)
def check_dns(system: System) -> list[Result]:
    shown = system.run(["resolvectl", "status"])
    if shown is None or shown.returncode != 0:
        return [Result(ID, TITLE, Status.SKIP, "systemd-resolved is not in use here.")]
    mode = parse_resolv_conf_mode(shown.stdout)
    if mode is None:
        return [Result(ID, TITLE, Status.SKIP, "Could not read resolvectl's resolv.conf mode.")]

    if mode == "stub":
        return [Result(ID, TITLE, Status.PASS, "/etc/resolv.conf points at systemd-resolved's stub.")]
    if mode == "missing":
        return [Result(ID, TITLE, Status.FAIL,
                       "/etc/resolv.conf does not exist, so programs that read it directly cannot resolve names.",
                       _fix(system))]

    nm = system.run(NM_DNS)
    nm_mode = parse_nm_dns_mode(nm.stdout) if nm is not None and nm.returncode == 0 else None
    if mode == "foreign" and nm_mode == "systemd-resolved":
        return [Result(
            ID, TITLE, Status.WARN,
            "NetworkManager hands DNS to systemd-resolved, but /etc/resolv.conf is a plain file rather "
            "than a link to resolved's stub. Lookups work today, but Tailscale reports this and MagicDNS "
            "can break.",
            _fix(system),
        )]
    return [Result(ID, TITLE, Status.SKIP,
                   f"/etc/resolv.conf mode is '{mode}' and looks intentional, so it was not checked further.")]
