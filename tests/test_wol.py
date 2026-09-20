from conftest import fixture, ok

from moonlight_host_doctor.checks.wol import (
    check_wol,
    parse_active_connections,
    parse_ethtool_wol,
    wired_interfaces,
)
from moonlight_host_doctor.model import Status

NET = "/sys/class/net"
NMCLI_ACTIVE = "nmcli -t -f NAME,TYPE,DEVICE connection show --active"
NMCLI_WOL = ("nmcli", "-g", "802-3-ethernet.wake-on-lan", "connection", "show", "Wired connection 2")


def machine(make, ethtool_fixture, nm_wol=None):
    """The real machine's layout: one wired NIC, one wifi card, and virtual interfaces."""
    commands = {
        "ethtool enp6s0": ok(fixture(ethtool_fixture)),
        NMCLI_ACTIVE: ok(fixture("nmcli_active.txt")),
    }
    if nm_wol:
        commands[NMCLI_WOL] = ok(fixture(nm_wol))
    return make(
        commands,
        paths={f"{NET}/enp6s0/device", f"{NET}/wlan0/device", f"{NET}/wlan0/wireless"},
        dirs={NET: ["docker0", "enp6s0", "lo", "tailscale0", "virbr0", "wlan0"]},
    )


def test_parse_ethtool_reads_real_privileged_output():
    assert parse_ethtool_wol(fixture("ethtool_wol_g.txt")) == ("pumbg", "g")


def test_parse_ethtool_returns_none_without_root():
    assert parse_ethtool_wol(fixture("ethtool_unprivileged.txt")) is None


def test_parse_active_connections_handles_names_with_colons():
    text = "Home\\: 5G:802-3-ethernet:enp6s0\nlo:loopback:lo\n"
    assert parse_active_connections(text)["enp6s0"] == "Home: 5G"


def test_only_physical_wired_interfaces_are_checked(make):
    system = machine(make, "ethtool_wol_g.txt")
    assert wired_interfaces(system) == ["enp6s0"]


def test_wake_on_magic_passes_and_mentions_the_bios_limit(make):
    [result] = check_wol(machine(make, "ethtool_wol_g.txt"))
    assert result.status is Status.PASS
    assert "BIOS" in result.detail


def test_wake_disabled_fails_with_temporary_and_persistent_fixes(make):
    [result] = check_wol(machine(make, "ethtool_wol_disabled.txt"))
    assert result.status is Status.FAIL
    assert result.fix[0].startswith("sudo ethtool -s enp6s0 wol g")
    assert 'nmcli connection modify "Wired connection 2"' in result.fix[1]


def test_unsupported_nic_fails_without_a_bogus_fix(make):
    text = fixture("ethtool_wol_g.txt").replace("pumbg", "d").replace("Wake-on: g", "Wake-on: d")
    system = machine(make, "ethtool_wol_g.txt")
    system.commands[("ethtool", "enp6s0")] = ok(text)
    [result] = check_wol(system)
    assert result.status is Status.FAIL
    assert result.fix == ()


def test_without_root_falls_back_to_networkmanager_and_says_it_is_unconfirmed(make):
    system = machine(make, "ethtool_unprivileged.txt", nm_wol="nmcli_wol_magic.txt")
    [result] = check_wol(system)
    assert result.status is Status.PASS
    assert "without root" in result.detail


def test_networkmanager_ignore_warns_rather_than_fails_when_nic_is_unreadable(make):
    system = machine(make, "ethtool_unprivileged.txt", nm_wol="nmcli_wol_ignore.txt")
    [result] = check_wol(system)
    assert result.status is Status.WARN


def test_unreadable_nic_and_no_networkmanager_is_skipped(make):
    system = machine(make, "ethtool_unprivileged.txt")
    del system.commands[tuple(NMCLI_ACTIVE.split())]
    [result] = check_wol(system)
    assert result.status is Status.SKIP


def test_machine_without_a_wired_nic_is_skipped(make):
    assert check_wol(make({}))[0].status is Status.SKIP
