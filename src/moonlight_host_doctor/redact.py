"""Mask details that identify you or your network, for pasting output into public issues.

Covers Tailscale (*.ts.net) names, IPv4 and IPv6 addresses and MAC addresses. It does not
cover interface names, NetworkManager connection names, or your hostname, so read the
output once before you post it.
"""

from __future__ import annotations

import re
from dataclasses import replace
from ipaddress import IPv6Address

from .model import Result

# The tailnet address range is a public constant, not something private, and the
# tailscale check quotes it in its explanations.
KEEP = {"100.64.0.0/10"}

_TSNET = re.compile(r"\b(?:[A-Za-z0-9-]+\.)?[A-Za-z0-9-]+\.ts\.net\b")
# Not followed by another digit or ".digit", so an address ending a sentence is still caught.
_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?(?!\d|\.\d)")
# Anything shaped like hex and colons; only what Python parses as IPv6 is masked, so times
# such as 12:30:45 and MAC-like strings are left to their own rules.
_IPV6 = re.compile(r"(?<![\w:])[0-9A-Fa-f:]{3,}(?:/\d{1,3})?(?![\w:])")
_MAC = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")


def _tsnet(match: re.Match) -> str:
    return "<host>.<tailnet>.ts.net" if match.group(0).count(".") >= 3 else "<tailnet>.ts.net"


def _ipv6(match: re.Match) -> str:
    address = match.group(0).partition("/")[0]
    try:
        IPv6Address(address)
    except ValueError:
        return match.group(0)
    return "<ipv6>"


def redact(text: str) -> str:
    text = _TSNET.sub(_tsnet, text)
    text = _MAC.sub("<mac>", text)
    text = _IPV4.sub(lambda m: m.group(0) if m.group(0) in KEEP else "<ipv4>", text)
    return _IPV6.sub(_ipv6, text)


def redact_result(result: Result) -> Result:
    return replace(
        result,
        title=redact(result.title),
        detail=redact(result.detail),
        fix=tuple(redact(step) for step in result.fix),
    )
