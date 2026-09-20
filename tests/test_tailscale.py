import json

import pytest
from conftest import fail, fixture, ok

from moonlight_host_doctor.checks.ports import UfwRule
from moonlight_host_doctor.checks.tailscale import check_tailscale, reaches_tailnet
from moonlight_host_doctor.model import Status

STATUS = "tailscale status --json"
LOOKUP = ("getent", "hosts", "linux.tail-example.ts.net")
UFW_LAN_ONLY = (
    "Status: active\n\n"
    "To                         Action      From\n"
    "--                         ------      ----\n"
    "47984,47989,48010/tcp      ALLOW       192.168.1.0/24\n"
    "47998:48000/udp            ALLOW       192.168.1.0/24\n"
)


def machine(make, status_fixture="tailscale_status_healthy.json", resolves=True, ufw=None):
    commands = {STATUS: ok(fixture(status_fixture))}
    commands[LOOKUP] = ok(fixture("getent_tailscale_name.txt")) if resolves else fail(code=2)
    if ufw is not None:
        commands["ufw status"] = ufw
    return make(commands)


def by_title(results):
    return {r.title: r for r in results}


def test_real_status_on_the_real_machine_reports_the_health_warning_and_a_working_name(make):
    system = machine(make, "tailscale_status_real.json", ufw=ok(fixture("ufw_active_real.txt")))
    results = by_title(check_tailscale(system))
    assert results["Tailscale connection"].status is Status.PASS
    assert "linux.tail-example.ts.net" in results["Tailscale connection"].detail
    assert "100.64.0.10" in results["Tailscale connection"].detail
    health = results["Tailscale health"]
    assert health.status is Status.WARN and "resolved-nm" in health.detail
    assert "does resolve here" in health.detail
    assert results["Tailscale MagicDNS"].status is Status.PASS
    assert results["Tailscale firewall"].status is Status.PASS


def test_no_health_message_means_no_health_result(make):
    results = by_title(check_tailscale(machine(make, ufw=ok(fixture("ufw_active_real.txt")))))
    assert "Tailscale health" not in results


def test_not_installed_is_skipped_not_failed(make):
    [result] = check_tailscale(make({}))
    assert result.status is Status.SKIP


def test_daemon_not_running_fails_with_the_service_fix(make):
    [result] = check_tailscale(make({STATUS: fail("failed to connect to local tailscaled")}))
    assert result.status is Status.FAIL
    assert result.fix == ("sudo systemctl enable --now tailscaled",)


@pytest.mark.parametrize("name", ["tailscale_status_needslogin.json", "tailscale_status_stopped.json"])
def test_logged_out_or_stopped_fails_and_stops_before_later_checks(make, name):
    [result] = check_tailscale(machine(make, name))
    assert result.status is Status.FAIL
    assert result.fix == ("sudo tailscale up",)


def test_magicdns_off_warns_that_clients_need_the_ip(make):
    results = by_title(check_tailscale(machine(make, "tailscale_status_magicdns_off.json")))
    assert results["Tailscale MagicDNS"].status is Status.WARN


def test_name_that_does_not_resolve_fails(make):
    results = by_title(check_tailscale(machine(make, resolves=False)))
    assert results["Tailscale MagicDNS"].status is Status.FAIL


def test_unresolvable_health_warning_does_not_claim_the_name_works(make):
    results = by_title(check_tailscale(machine(make, "tailscale_status_real.json", resolves=False)))
    assert "does resolve here" not in results["Tailscale health"].detail


def test_garbage_output_becomes_a_warning(make):
    [result] = check_tailscale(make({STATUS: ok("not json")}))
    assert result.status is Status.WARN


def test_lan_only_ufw_rules_block_tailnet_clients_and_the_fix_targets_tailscale0(make):
    results = by_title(check_tailscale(machine(make, ufw=ok(UFW_LAN_ONLY))))
    firewall = results["Tailscale firewall"]
    assert firewall.status is Status.FAIL
    assert firewall.fix == (
        "sudo ufw allow in on tailscale0 to any port 47984,47989,48010 proto tcp",
        "sudo ufw allow in on tailscale0 to any port 47998,47999,48000 proto udp",
    )


def test_ufw_needing_root_is_skipped(make):
    results = by_title(check_tailscale(machine(make, ufw=fail("ERROR: You need to be root"))))
    assert results["Tailscale firewall"].status is Status.SKIP


def test_no_ufw_is_skipped_and_inactive_ufw_passes(make):
    assert by_title(check_tailscale(machine(make)))["Tailscale firewall"].status is Status.SKIP
    inactive = machine(make, ufw=ok(fixture("ufw_inactive.txt")))
    assert by_title(check_tailscale(inactive))["Tailscale firewall"].status is Status.PASS


@pytest.mark.parametrize(
    "rule, expected",
    [
        (UfwRule("tcp", 1, 1, None, None), True),  # from anywhere
        (UfwRule("tcp", 1, 1, "100.64.0.0/10", None), True),
        (UfwRule("tcp", 1, 1, "100.100.0.0/16", None), True),  # inside the tailnet range
        (UfwRule("tcp", 1, 1, "192.168.1.0/24", None), False),  # LAN only
        (UfwRule("tcp", 1, 1, "192.168.1.0/24", "tailscale0"), True),  # the interface decides
        (UfwRule("tcp", 1, 1, None, "enp6s0"), False),  # scoped to another NIC
        (UfwRule("tcp", 1, 1, "not-an-address", None), False),
    ],
)
def test_reaches_tailnet(rule, expected):
    assert reaches_tailnet(rule) is expected


def test_fixtures_are_valid_and_contain_no_key_material():
    for name in ("real", "healthy", "needslogin", "stopped", "magicdns_off"):
        text = fixture(f"tailscale_status_{name}.json")
        json.loads(text)
        assert "nodekey" not in text and "PublicKey" not in text
