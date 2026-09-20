# Test fixtures

Saved command output the checks are tested against.

**Captured from a real machine** (CachyOS, KDE Plasma, Sunshine 2026.914, Realtek 2.5G NIC):
`systemctl_user_sunshine_running.txt`, `ss_tcp_sunshine_listening.txt` (pids replaced),
`ethtool_wol_g.txt`, `ethtool_unprivileged.txt`, `nmcli_active.txt`, `nmcli_wol_magic.txt`,
`ufw_active_real.txt` (only the private LAN range was replaced with 192.168.1.0/24),
`tailscale_status_real.json` (Tailscale 1.102.4; tailnet name, IPs and all key material replaced or dropped),
`getent_tailscale_name.txt` (name and IP replaced),
`kreadconfig_false.txt` (KDE screen-lock settings, both false on that machine),
`resolvectl_mode_foreign.txt` and `busctl_nm_dns_resolved.txt` (the broken state, before the fix),
`resolvectl_mode_stub.txt` (after the fix; first three lines of `resolvectl status` only).

**Derived by editing a real capture:** `ethtool_wol_disabled.txt` (Wake-on changed to `d`), `ufw_real_without_udp.txt`
(real ufw output with the UDP streaming rules removed), `tailscale_status_healthy.json`,
`kreadconfig_true.txt` and `kreadconfig_timeout_5.txt` (the values written by hand; not observed as set),
`resolvectl_mode_missing.txt` (the real line seen when the file was deleted, put in the real header),
`busctl_nm_dns_dnsmasq.txt` (real capture with the mode changed), `_needslogin.json`, `_stopped.json` and `_magicdns_off.json` (the real capture with the health message
removed or one field changed; the login and stopped states were not observed on a real system).

**Hand-written from the documented format, NOT captured from a real system:**
`ufw_inactive.txt`, `nmcli_wol_ignore.txt`. firewalld output is not captured anywhere yet,
so its parser is only tested against strings written in `tests/test_ports.py`. Real output
from other setups is welcome (remove anything private first).
