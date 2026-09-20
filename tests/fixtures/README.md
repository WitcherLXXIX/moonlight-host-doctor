# Test fixtures

Saved command output the checks are tested against.

**Captured from a real machine** (CachyOS, KDE Plasma, Sunshine 2026.914, Realtek 2.5G NIC):
`systemctl_user_sunshine_running.txt`, `ss_tcp_sunshine_listening.txt` (pids replaced),
`ethtool_wol_g.txt`, `ethtool_unprivileged.txt`, `nmcli_active.txt`, `nmcli_wol_magic.txt`,
`ufw_active_real.txt` (only the private LAN range was replaced with 192.168.1.0/24).

**Derived by editing a real capture:** `ethtool_wol_disabled.txt` (Wake-on changed to `d`), `ufw_real_without_udp.txt`
(real ufw output with the UDP streaming rules removed).

**Hand-written from the documented format, NOT captured from a real system:**
`ufw_inactive.txt`, `nmcli_wol_ignore.txt`. firewalld output is not captured anywhere yet,
so its parser is only tested against strings written in `tests/test_ports.py`. Real output
from other setups is welcome (remove anything private first).
