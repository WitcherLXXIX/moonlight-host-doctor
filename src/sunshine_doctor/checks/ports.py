"""Is Sunshine listening, and does the firewall let a client reach it?

Assumes Sunshine's default base port (47989). The UDP streaming ports only exist
while a stream is running, so they are checked against the firewall and never
against listening sockets.
"""

from __future__ import annotations

import re

from ..model import Result, Status, check
from ..system import System

LISTEN_ID = "listening"
LISTEN_TITLE = "Sunshine listening ports"
FIREWALL_ID = "firewall"
FIREWALL_TITLE = "Firewall"

TCP_PORTS = (47984, 47989, 48010)
UDP_PORTS = (47998, 47999, 48000, 48002, 48010)

# (protocol, first port, last port)
Rule = tuple[str, int, int]


def parse_listening_tcp(text: str) -> set[int]:
    """Ports from `ss -H -tln` output. Local address is the fourth column."""
    ports = set()
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 4 and ":" in fields[3]:
            tail = fields[3].rsplit(":", 1)[1]
            if tail.isdigit():
                ports.add(int(tail))
    return ports


def _port_spec(spec: str) -> list[tuple[int, int]] | None:
    """'47984,47989' or '47998:48000' or '47998-48000' to a list of ranges."""
    ranges = []
    for part in spec.split(","):
        bounds = re.split(r"[:-]", part)
        if not all(b.isdigit() for b in bounds) or len(bounds) > 2:
            return None
        ranges.append((int(bounds[0]), int(bounds[-1])))
    return ranges


def parse_ufw(text: str) -> tuple[bool, list[Rule]]:
    """Returns (active, allow rules) from `ufw status` output. IPv6 rules are skipped."""
    if re.search(r"^Status:\s*inactive", text, re.MULTILINE):
        return False, []
    rules: list[Rule] = []
    for line in text.splitlines():
        if "(v6)" in line:
            continue
        match = re.match(r"^(\S+)\s+ALLOW(?:\s+IN)?\s", line)
        if not match:
            continue
        spec = match.group(1)
        spec, _, proto = spec.partition("/")
        ranges = _port_spec(spec)
        if ranges is None:
            continue  # an app profile name or "Anywhere"
        for proto_name in ((proto,) if proto in ("tcp", "udp") else ("tcp", "udp")):
            rules.extend((proto_name, lo, hi) for lo, hi in ranges)
    return True, rules


def parse_firewalld_ports(text: str) -> list[Rule]:
    """Rules from `firewall-cmd --list-ports`, for example '47984/tcp 47998-48000/udp'."""
    rules: list[Rule] = []
    for item in text.split():
        spec, _, proto = item.partition("/")
        ranges = _port_spec(spec)
        if ranges is None or proto not in ("tcp", "udp"):
            continue
        rules.extend((proto, lo, hi) for lo, hi in ranges)
    return rules


def missing_ports(rules: list[Rule]) -> dict[str, list[int]]:
    """Which required ports no rule covers, keyed by protocol."""
    missing: dict[str, list[int]] = {}
    for proto, ports in (("tcp", TCP_PORTS), ("udp", UDP_PORTS)):
        gaps = [
            p for p in ports
            if not any(r[0] == proto and r[1] <= p <= r[2] for r in rules)
        ]
        if gaps:
            missing[proto] = gaps
    return missing


def _describe(missing: dict[str, list[int]]) -> str:
    return "; ".join(
        f"{proto.upper()} {', '.join(map(str, ports))}" for proto, ports in missing.items()
    )


@check(LISTEN_ID)
def check_listening(system: System) -> list[Result]:
    listed = system.run(["ss", "-H", "-tln"])
    if listed is None or listed.returncode != 0:
        return [Result(LISTEN_ID, LISTEN_TITLE, Status.SKIP, "`ss` is not available here.")]
    absent = [p for p in TCP_PORTS if p not in parse_listening_tcp(listed.stdout)]
    if absent:
        return [
            Result(
                LISTEN_ID, LISTEN_TITLE, Status.FAIL,
                f"Nothing is listening on TCP {', '.join(map(str, absent))}. "
                "Sunshine is not running, or uses a different base port.",
                ("Run the 'Sunshine service' check first.",),
            )
        ]
    return [Result(LISTEN_ID, LISTEN_TITLE, Status.PASS, "TCP ports are open on this machine.")]


@check(FIREWALL_ID)
def check_firewall(system: System) -> list[Result]:
    if system.has_command("ufw"):
        status = system.run(["ufw", "status"])
        if status is None or status.returncode != 0:
            return [
                Result(
                    FIREWALL_ID, FIREWALL_TITLE, Status.SKIP,
                    "ufw is installed but its rules need root to read.",
                    ("sudo sunshine-doctor --only firewall",),
                )
            ]
        active, rules = parse_ufw(status.stdout)
        if not active:
            return [Result(FIREWALL_ID, FIREWALL_TITLE, Status.PASS, "ufw is inactive, so it blocks nothing.")]
        gaps = missing_ports(rules)
        if not gaps:
            return [Result(FIREWALL_ID, FIREWALL_TITLE, Status.PASS, "ufw allows the Sunshine ports.")]
        return [
            Result(
                FIREWALL_ID, FIREWALL_TITLE, Status.FAIL,
                f"ufw has no allow rule for {_describe(gaps)}.",
                tuple(
                    f"sudo ufw allow {','.join(map(str, ports))}/{proto}"
                    for proto, ports in gaps.items()
                ),
            )
        ]

    if system.has_command("firewall-cmd"):
        state = system.run(["firewall-cmd", "--state"])
        if state is None or state.returncode != 0 or "running" not in state.stdout:
            return [Result(FIREWALL_ID, FIREWALL_TITLE, Status.PASS, "firewalld is not running, so it blocks nothing.")]
        listed = system.run(["firewall-cmd", "--list-ports"])
        if listed is None or listed.returncode != 0:
            return [Result(FIREWALL_ID, FIREWALL_TITLE, Status.SKIP, "Could not read the firewalld ports.")]
        gaps = missing_ports(parse_firewalld_ports(listed.stdout))
        if not gaps:
            return [Result(FIREWALL_ID, FIREWALL_TITLE, Status.PASS, "firewalld allows the Sunshine ports.")]
        adds = " ".join(
            f"--add-port={p}/{proto}" for proto, ports in gaps.items() for p in ports
        )
        return [
            Result(
                FIREWALL_ID, FIREWALL_TITLE, Status.FAIL,
                f"firewalld has no rule for {_describe(gaps)} in the default zone.",
                (f"sudo firewall-cmd --permanent {adds}", "sudo firewall-cmd --reload"),
            )
        ]

    return [
        Result(
            FIREWALL_ID, FIREWALL_TITLE, Status.SKIP,
            "No ufw or firewalld found. Raw nftables or iptables rules are not checked.",
        )
    ]
