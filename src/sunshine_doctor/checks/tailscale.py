"""Can a client reach this host over Tailscale?

Tailscale is optional, so a machine without it is skipped, never failed. The checks
run in the order a connection breaks: the daemon, what Tailscale itself reports, the
MagicDNS name, then whether the firewall lets tailnet addresses in.
"""

from __future__ import annotations

import json
from ipaddress import ip_network

from ..model import Result, Status, check
from ..system import System
from .ports import UfwRule, missing_ports, parse_ufw_rules

ID = "tailscale"
TITLE = "Tailscale"
CGNAT = ip_network("100.64.0.0/10")  # the range every tailnet IPv4 address comes from


def reaches_tailnet(rule: UfwRule) -> bool:
    """Whether a ufw rule can admit a client arriving over Tailscale."""
    if rule.iface is not None:
        return rule.iface == "tailscale0"
    if rule.source is None:
        return True
    try:
        source = ip_network(rule.source, strict=False)
    except ValueError:
        return False
    return source.version == 4 and source.overlaps(CGNAT)


def _ipv4(status: dict) -> str | None:
    return next((ip for ip in status.get("TailscaleIPs") or [] if "." in ip), None)


def _daemon_result(status: dict) -> Result:
    state = status.get("BackendState", "unknown")
    if state == "Running":
        if status.get("Self", {}).get("Online") is False:
            return Result(ID, f"{TITLE} connection", Status.WARN,
                          "Tailscale is running but this machine shows as offline in the tailnet.")
        ip = _ipv4(status)
        name = status.get("Self", {}).get("DNSName", "").rstrip(".")
        where = f"{name} or {ip}" if name and ip else name or ip or "no address yet"
        return Result(ID, f"{TITLE} connection", Status.PASS,
                      f"Connected. Clients on the tailnet can use {where}.")
    if state == "NeedsLogin":
        return Result(ID, f"{TITLE} connection", Status.FAIL,
                      "This machine is logged out of Tailscale.", ("sudo tailscale up",))
    if state == "Stopped":
        return Result(ID, f"{TITLE} connection", Status.FAIL,
                      "Tailscale is stopped.", ("sudo tailscale up",))
    return Result(ID, f"{TITLE} connection", Status.WARN, f"Tailscale is in state '{state}'.")


def _dns_result(status: dict, resolves: bool | None) -> Result:
    title = f"{TITLE} MagicDNS"
    tailnet = status.get("CurrentTailnet") or {}
    if tailnet.get("MagicDNSEnabled") is False:
        return Result(ID, title, Status.WARN,
                      "MagicDNS is off for this tailnet, so clients must use the IP address.")
    name = status.get("Self", {}).get("DNSName", "").rstrip(".")
    if not name or resolves is None:
        return Result(ID, title, Status.SKIP, "Could not test name resolution here.")
    if resolves:
        return Result(ID, title, Status.PASS, f"{name} resolves on this machine.")
    return Result(
        ID, title, Status.FAIL,
        f"{name} does not resolve on this machine.",
        ("resolvectl status tailscale0", "See https://tailscale.com/s/resolved-nm"),
    )


def _firewall_result(system: System) -> Result:
    title = f"{TITLE} firewall"
    if not system.has_command("ufw"):
        return Result(ID, title, Status.SKIP, "Only ufw is checked for tailnet access so far.")
    shown = system.run(["ufw", "status"])
    if shown is None or shown.returncode != 0:
        return Result(ID, title, Status.SKIP, "ufw's rules need root to read.",
                      ("sudo sunshine-doctor --only tailscale",))
    active, rules = parse_ufw_rules(shown.stdout)
    if not active:
        return Result(ID, title, Status.PASS, "ufw is inactive, so it blocks nothing.")
    gaps = missing_ports([(r.proto, r.lo, r.hi) for r in rules if reaches_tailnet(r)])
    if not gaps:
        return Result(ID, title, Status.PASS, "ufw lets tailnet clients reach the Sunshine ports.")
    listing = "; ".join(f"{p.upper()} {', '.join(map(str, ports))}" for p, ports in gaps.items())
    return Result(
        ID, title, Status.FAIL,
        f"ufw only allows {listing} from other sources, so a client on your tailnet "
        "(100.64.0.0/10) is blocked.",
        tuple(
            f"sudo ufw allow in on tailscale0 to any port {','.join(map(str, ports))} proto {proto}"
            for proto, ports in gaps.items()
        ),
    )


@check(ID)
def check_tailscale(system: System) -> list[Result]:
    shown = system.run(["tailscale", "status", "--json"])
    if shown is None:
        return [Result(ID, TITLE, Status.SKIP, "Tailscale is not installed, so it was not checked.")]
    if shown.returncode != 0:
        return [
            Result(ID, f"{TITLE} connection", Status.FAIL,
                   "The tailscaled service is not running.",
                   ("sudo systemctl enable --now tailscaled",))
        ]
    try:
        status = json.loads(shown.stdout)
    except json.JSONDecodeError:
        return [Result(ID, TITLE, Status.WARN, "Could not read `tailscale status --json`.")]

    results = [_daemon_result(status)]
    if status.get("BackendState") != "Running":
        return results

    name = status.get("Self", {}).get("DNSName", "").rstrip(".")
    lookup = system.run(["getent", "hosts", name]) if name else None
    resolves = None if lookup is None else (lookup.returncode == 0 and bool(lookup.stdout.strip()))

    for message in status.get("Health") or []:
        note = " (The name does resolve here, so this may not affect you.)" if resolves else ""
        results.append(Result(ID, f"{TITLE} health", Status.WARN, f"Tailscale reports: {message}{note}"))
    results.append(_dns_result(status, resolves))
    results.append(_firewall_result(system))
    return results
