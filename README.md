# sunshine-doctor

Read-only checks for a [Sunshine](https://github.com/LizardByte/Sunshine) game-streaming host on Linux.
When a Moonlight client cannot connect or cannot wake the host, it tells you which layer is broken and
prints the command that fixes it. It never runs a fix itself and needs no root for most checks.

```
$ sunshine-doctor
[ OK ] Sunshine service: app-dev.lizardbyte.app.Sunshine.service is running.
[ OK ] Sunshine listening ports: TCP ports are open on this machine.
[SKIP] Firewall: ufw is installed but its rules need root to read.
       fix: sudo sunshine-doctor --only firewall
[ OK ] Wake-on-LAN (enp6s0): NetworkManager sets "Wired connection 2" to magic. ...
```

Status: **early, v0.1.** Not affiliated with LizardByte or Moonlight.

## Checks

| Check | Looks at | Needs root |
|---|---|---|
| `service` | Sunshine user service is installed and running | no |
| `listening` | Sunshine is listening on its TCP ports | no |
| `firewall` | ufw or firewalld allows the TCP and UDP ports | ufw: yes |
| `wol` | Wired NIC is set to wake on a magic packet | to confirm at the NIC: yes |

Options: `--only CHECK` (repeatable), `--json`, `--list`. Exit status is 1 if any check failed.

## Limits you should know about

- Assumes Sunshine's default base port (47989). The required ports come from offsets in Sunshine's source:
  TCP 47984, 47989, 48010 and UDP 47998, 47999, 48000. The web UI (47990) and mic (48002) ports are not required.
- A firewall rule limited to one source or interface still counts as allowing the port, so a rule
  that only covers your LAN will not be flagged for a client arriving over Tailscale.
- The BIOS/UEFI wake-on-LAN option cannot be read from Linux, so a passing `wol` check does not
  guarantee waking from a full power-off.
- UDP streaming ports only exist during a stream, so they are checked against firewall rules, not sockets.
- Raw nftables/iptables rules are not checked, and neither are IPv6 rules.
- Verified on one machine: CachyOS, KDE Plasma (Wayland), NVIDIA, ufw, NetworkManager, Tailscale.
  The ufw parser is tested against real output from that machine; the firewalld parser only against
  strings written for the tests (see `tests/fixtures/README.md`). Reports and real output from other
  setups are the most useful contribution.

## Development

```
python -m venv .venv && .venv/bin/pip install -e '.[test]'
.venv/bin/python -m pytest
```

Checks read the machine only through `System` (`src/sunshine_doctor/system.py`), so tests use saved
command output and never need real hardware. To add a check, write a function decorated with
`@check("id")` that returns a list of `Result`, and import its module in `checks/__init__.py`.

## License

GPL-3.0-or-later, the same as Sunshine.
