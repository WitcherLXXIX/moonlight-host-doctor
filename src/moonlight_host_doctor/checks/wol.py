"""Can this machine be woken by a magic packet?

Reading the NIC's Wake-on state with ethtool needs root. Without root we fall back
to NetworkManager's setting, which does not prove what the NIC is doing.
The BIOS/UEFI wake option cannot be read from Linux at all.
"""

from __future__ import annotations

import re

from ..model import Result, Status, check
from ..system import System

ID = "wol"
TITLE = "Wake-on-LAN"
NET = "/sys/class/net"
BIOS_NOTE = (
    "Waking from a full power-off also needs the BIOS/UEFI wake-on-LAN option, "
    "which Linux cannot read."
)


def parse_ethtool_wol(text: str) -> tuple[str, str] | None:
    """(supported flags, current flags), or None when ethtool printed no Wake-on lines."""
    supports = re.search(r"^\s*Supports Wake-on:\s*(\S+)", text, re.MULTILINE)
    current = re.search(r"^\s*Wake-on:\s*(\S+)", text, re.MULTILINE)
    if not supports or not current:
        return None
    return supports.group(1), current.group(1)


def parse_active_connections(text: str) -> dict[str, str]:
    """Map device to connection name from `nmcli -t -f NAME,TYPE,DEVICE connection show --active`."""
    devices = {}
    for line in text.splitlines():
        parts = line.rsplit(":", 2)
        if len(parts) == 3:
            devices[parts[2]] = parts[0].replace("\\:", ":")
    return devices


def wired_interfaces(system: System) -> list[str]:
    """Physical, non-wireless interfaces. Virtual ones (docker, tailscale) have no device link."""
    return [
        name for name in system.list_dir(NET)
        if system.path_exists(f"{NET}/{name}/device")
        and not system.path_exists(f"{NET}/{name}/wireless")
    ]


def _fix(nic: str, connection: str | None) -> tuple[str, ...]:
    steps = [f"sudo ethtool -s {nic} wol g  # until the next reboot"]
    if connection:
        steps.append(
            f'nmcli connection modify "{connection}" 802-3-ethernet.wake-on-lan magic'
            "  # persistent"
        )
    else:
        steps.append("Set the connection's wake-on-lan option to 'magic' to make it persistent.")
    return tuple(steps)


def _from_networkmanager(system: System, nic: str, connection: str | None) -> Result:
    unconfirmed = f"Cannot read {nic}'s Wake-on state without root."
    rerun = ("sudo moonlight-host-doctor --only wol",)
    if connection is None:
        return Result(ID, f"{TITLE} ({nic})", Status.SKIP, unconfirmed, rerun)
    value = system.run(["nmcli", "-g", "802-3-ethernet.wake-on-lan", "connection", "show", connection])
    if value is None or value.returncode != 0:
        return Result(ID, f"{TITLE} ({nic})", Status.SKIP, unconfirmed, rerun)
    setting = value.stdout.strip()
    if "magic" in setting:
        return Result(
            ID, f"{TITLE} ({nic})", Status.PASS,
            f'NetworkManager sets "{connection}" to magic. {unconfirmed} {BIOS_NOTE}',
        )
    return Result(
        ID, f"{TITLE} ({nic})", Status.WARN,
        f'NetworkManager sets "{connection}" to "{setting}", not magic. {unconfirmed}',
        _fix(nic, connection),
    )


@check(ID)
def check_wol(system: System) -> list[Result]:
    nics = wired_interfaces(system)
    if not nics:
        return [Result(ID, TITLE, Status.SKIP, "No wired network interface found.")]

    connections: dict[str, str] = {}
    active = system.run(["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"])
    if active is not None and active.returncode == 0:
        connections = parse_active_connections(active.stdout)

    results = []
    for nic in nics:
        title = f"{TITLE} ({nic})"
        shown = system.run(["ethtool", nic])
        if shown is None:
            results.append(Result(ID, title, Status.SKIP, "ethtool is not installed."))
            continue
        wol = parse_ethtool_wol(shown.stdout)
        if wol is None:
            results.append(_from_networkmanager(system, nic, connections.get(nic)))
            continue
        supported, current = wol
        if "g" not in supported:
            results.append(
                Result(
                    ID, title, Status.FAIL,
                    f"{nic} does not report magic-packet support (supports: {supported}). "
                    "Check the BIOS/UEFI wake-on-LAN option and the network driver.",
                )
            )
        elif "g" not in current:
            results.append(
                Result(ID, title, Status.FAIL,
                       f"{nic} supports magic packets but is set to '{current}'.",
                       _fix(nic, connections.get(nic)))
            )
        else:
            results.append(Result(ID, title, Status.PASS, f"{nic} is set to wake on magic packet. {BIOS_NOTE}"))
    return results
