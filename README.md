# moonlight-host-doctor

Read-only checks for a [Sunshine](https://github.com/LizardByte/Sunshine) game-streaming host on Linux.
When a Moonlight client cannot connect or cannot wake the host, it tells you which layer is broken and
prints the command that fixes it. It never runs a fix itself and needs no root for most checks.

```
$ moonlight-host-doctor
[ OK ] Sunshine service: app-dev.lizardbyte.app.Sunshine.service is running.
[ OK ] Sunshine listening ports: TCP ports are open on this machine.
[SKIP] Firewall: ufw is installed but its rules need root to read.
       fix: sudo env "PATH=$PATH" moonlight-host-doctor --only firewall
[ OK ] Wake-on-LAN (enp6s0): NetworkManager sets "Wired connection 2" to magic. ...
```

Status: **early, v0.1.** Not affiliated with LizardByte or Moonlight.

## Install

Needs Python 3.10 or newer and nothing else. It is not on PyPI yet, so install straight from GitHub.
[pipx](https://pipx.pypa.io) keeps it in its own environment:

```
pipx install git+https://github.com/WitcherLXXIX/moonlight-host-doctor
```

`pipx` is packaged by most distributions (`sudo pacman -S python-pipx` on Arch and CachyOS). Without it,
a plain virtual environment works the same way:

```
python -m venv ~/.local/share/moonlight-host-doctor
~/.local/share/moonlight-host-doctor/bin/pip install git+https://github.com/WitcherLXXIX/moonlight-host-doctor
~/.local/share/moonlight-host-doctor/bin/moonlight-host-doctor
```

Remove it with `pipx uninstall moonlight-host-doctor`.

### Running the checks that need root

A few checks (ufw rules, the NIC's Wake-on setting) can only be read as root. Run just those with sudo, and
pass your `PATH` through so sudo can find a user-level install:

```
sudo env "PATH=$PATH" moonlight-host-doctor --only firewall --only wol --only tailscale
```

Do not run the whole tool under sudo: the `service` check asks about *your* user services, and root cannot see
them, so it skips itself with a note. This works the same in bash, zsh and fish.

## Checks

| Check | Looks at | Needs root |
|---|---|---|
| `service` | Sunshine user service is installed and running | no |
| `listening` | Sunshine is listening on its TCP ports | no |
| `firewall` | ufw or firewalld allows the TCP and UDP ports | ufw: yes |
| `wol` | Wired NIC is set to wake on a magic packet | to confirm at the NIC: yes |
| `lock` | Whether the KDE screen lock will greet a Moonlight client after a wake or idle (information only, KDE Plasma only) | no |
| `dns` | systemd-resolved and NetworkManager agree about `/etc/resolv.conf` (a leftover plain file is the usual cause of Tailscale's "wired together incorrectly" warning) | no |
| `tailscale` | Tailscale is connected, reports no problems, its MagicDNS name resolves here, and ufw admits tailnet clients (skipped if Tailscale is not installed) | ufw part: yes |

Options: `--only CHECK` (repeatable), `--json`, `--list`, `--redact`. Exit status is 1 if any check failed.

### Posting output publicly

Use `--redact` when you paste output into an issue or forum. It masks Tailscale names, IPv4 and IPv6
addresses and MAC addresses. It does **not** mask your hostname, interface names, or NetworkManager
connection names (people sometimes name a connection after their Wi-Fi network), so read the output
once before you post it.

## Reporting results

Output from setups other than the author's is the most useful contribution, including when the tool is wrong.
Open a [test report](https://github.com/WitcherLXXIX/moonlight-host-doctor/issues/new?template=test-report.yml) with the output of
`moonlight-host-doctor --redact`.

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
- Tested on Python 3.10 and 3.14. The checks themselves are verified on one machine: CachyOS, KDE Plasma (Wayland), NVIDIA, ufw, NetworkManager, Tailscale.
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
