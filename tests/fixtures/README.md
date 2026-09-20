# Test fixtures

Saved command output the checks are tested against.

**Captured from a real machine** (CachyOS, KDE Plasma, Sunshine 2026.914, Realtek 2.5G NIC):
`systemctl_user_sunshine_running.txt`, `ss_tcp_sunshine_listening.txt` (pids replaced),
`ethtool_wol_g.txt`, `ethtool_unprivileged.txt`, `nmcli_active.txt`, `nmcli_wol_magic.txt`.

**Derived by editing a real capture:** `ethtool_wol_disabled.txt` (Wake-on changed to `d`).

**Hand-written from the documented format, NOT captured from a real system:**
`ufw_*.txt`, `nmcli_wol_ignore.txt`. Reading `ufw status` needs root. If you can,
please replace these with real output (remove anything private first).
