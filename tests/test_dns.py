from conftest import fail, fixture, ok

from moonlight_host_doctor.checks.dns import (
    NM_DNS,
    check_dns,
    parse_nm_dns_mode,
    parse_resolv_conf_mode,
)
from moonlight_host_doctor.model import Status

RESOLVECTL = "resolvectl status"


def machine(make, resolvectl, nm=None, tailscale=True):
    commands = {RESOLVECTL: ok(fixture(resolvectl))}
    if nm:
        commands[tuple(NM_DNS)] = ok(fixture(nm))
    if tailscale:
        commands["tailscale version"] = ok("1.102.4")
    return make(commands)


def test_parsers_read_real_output():
    assert parse_resolv_conf_mode(fixture("resolvectl_mode_foreign.txt")) == "foreign"
    assert parse_resolv_conf_mode(fixture("resolvectl_mode_stub.txt")) == "stub"
    assert parse_nm_dns_mode(fixture("busctl_nm_dns_resolved.txt")) == "systemd-resolved"
    assert parse_nm_dns_mode("nonsense") is None


def test_the_broken_state_from_the_real_machine_warns_with_a_symlink_fix_and_tailscale_restart(make):
    system = machine(make, "resolvectl_mode_foreign.txt", "busctl_nm_dns_resolved.txt")
    [result] = check_dns(system)
    assert result.status is Status.WARN
    assert result.fix == (
        "sudo ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf",
        "sudo systemctl restart tailscaled",
    )


def test_the_fixed_state_from_the_real_machine_passes(make):
    [result] = check_dns(machine(make, "resolvectl_mode_stub.txt"))
    assert result.status is Status.PASS


def test_a_missing_resolv_conf_fails(make):
    [result] = check_dns(machine(make, "resolvectl_mode_missing.txt"))
    assert result.status is Status.FAIL
    assert result.fix[0].startswith("sudo ln -sf")


def test_the_restart_step_is_left_out_when_tailscale_is_not_installed(make):
    system = machine(make, "resolvectl_mode_foreign.txt", "busctl_nm_dns_resolved.txt", tailscale=False)
    [result] = check_dns(system)
    assert result.fix == ("sudo ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf",)


def test_a_foreign_resolv_conf_is_left_alone_when_networkmanager_is_not_using_resolved(make):
    system = machine(make, "resolvectl_mode_foreign.txt", "busctl_nm_dns_dnsmasq.txt")
    [result] = check_dns(system)
    assert result.status is Status.SKIP


def test_a_foreign_resolv_conf_without_networkmanager_is_not_flagged(make):
    [result] = check_dns(machine(make, "resolvectl_mode_foreign.txt"))
    assert result.status is Status.SKIP


def test_no_systemd_resolved_is_skipped(make):
    assert check_dns(make({RESOLVECTL: fail()}))[0].status is Status.SKIP
    assert check_dns(make({}))[0].status is Status.SKIP
