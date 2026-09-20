# moonlight-host-doctor

Read-only checks for a [Sunshine](https://github.com/LizardByte/Sunshine) game-streaming host on Linux.
When a Moonlight client cannot connect or cannot wake the host, it tells you which layer is broken and
prints the command that fixes it. It never runs a fix itself and needs no root for most checks.

```
$ moonlight-host-doctor
[ OK ] Sunshine service: app-dev.lizardbyte.app.Sunshine.service is running.
[ OK ] Sunshine listening ports: TCP ports are open on this machine.
[SKIP] Firewall: ufw is installed but its rules need root to read.
       fix: sudo moonlight-host-doctor --only firewall
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
| `tailscale` | Tailscale is connected, reports no problems, its MagicDNS name resolves here, and ufw admits tailnet clients (skipped if Tailscale is not installed) | ufw part: yes |

Options: `--only CHECK` (repeatable), `--json`, `--list`, `--redact`. Exit status is 1 if any check failed.

### Posting output publicly

Use `--redact` when you paste output into an issue or forum. It masks Tailscale names, IPv4 and IPv6
addresses and MAC addresses. It does **not** mask your hostname, interface names, or NetworkManager
connection names (people sometimes name a connection after their Wi-Fi network), so read the output
once before you post it.

## Limits you should know about

- Assumes Sunshine's default base port (47989). The required ports come from offsets in Sunshine's source:
  TCP 47984, 47989, 48010 and UDP 47998, 47999, 48000. The web UI (47990) and mic (48002) ports are not required.
- The `firewall` check counts a rule limited to one source or interface as allowing the port. The
  `tailscale` check is stricter and flags rules that cannot admit a client from 100.64.0.0/10.
- Waking a host from outside its LAN needs another always-on device on that network (for example a
  Tailscale subnet router). That is not checked.
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

Checks read the machine only through `System` (`src/moonlight_host_doctor/system.py`), so tests use saved
command output and never need real hardware. To add a check, write a function decorated with
`@check("id")` that returns a list of `Result`, and import its module in `checks/__init__.py`.

## License

GPL-3.0-or-later, the same as Sunshine.
