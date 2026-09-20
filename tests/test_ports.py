from conftest import fail, fixture, ok

from sunshine_doctor.checks.ports import (
    check_firewall,
    check_listening,
    missing_ports,
    parse_firewalld_ports,
    parse_listening_tcp,
    parse_ufw,
)
from sunshine_doctor.model import Status


def test_parse_listening_tcp_reads_real_ss_output():
    ports = parse_listening_tcp(fixture("ss_tcp_sunshine_listening.txt"))
    assert ports == {47984, 47989, 47990, 48010}


def test_parse_listening_tcp_handles_ipv6_and_wildcard():
    text = "LISTEN 0 4096 [::]:47984 [::]:*\nLISTEN 0 4096 *:47989 *:*\n"
    assert parse_listening_tcp(text) == {47984, 47989}


def test_listening_passes_with_real_output(make):
    system = make({"ss -H -tln": ok(fixture("ss_tcp_sunshine_listening.txt"))})
    assert check_listening(system)[0].status is Status.PASS


def test_listening_fails_and_names_missing_ports(make):
    system = make({"ss -H -tln": ok("LISTEN 0 4096 0.0.0.0:47989 0.0.0.0:*\n")})
    [result] = check_listening(system)
    assert result.status is Status.FAIL
    assert "47984" in result.detail and "48010" in result.detail


def test_parse_ufw_expands_lists_ranges_and_protocols():
    active, rules = parse_ufw(fixture("ufw_active_allowed.txt"))
    assert active
    assert ("tcp", 47989, 47989) in rules
    assert ("udp", 47998, 48000) in rules
    assert missing_ports(rules) == {}


def test_parse_ufw_treats_a_rule_without_protocol_as_both():
    _, rules = parse_ufw("Status: active\n\n47989   ALLOW   Anywhere\n")
    assert ("tcp", 47989, 47989) in rules and ("udp", 47989, 47989) in rules


def test_parse_ufw_ignores_ipv6_duplicates_deny_rules_and_profiles():
    text = (
        "Status: active\n\n"
        "47984/tcp (v6)   ALLOW   Anywhere (v6)\n"
        "47989/tcp        DENY    Anywhere\n"
        "OpenSSH          ALLOW   Anywhere\n"
    )
    _, rules = parse_ufw(text)
    assert rules == []


def test_ufw_with_all_ports_allowed_passes(make):
    system = make({"ufw status": ok(fixture("ufw_active_allowed.txt"))})
    assert check_firewall(system)[0].status is Status.PASS


def test_ufw_missing_udp_fails_with_a_copyable_fix(make):
    system = make({"ufw status": ok(fixture("ufw_active_missing_udp.txt"))})
    [result] = check_firewall(system)
    assert result.status is Status.FAIL
    assert result.fix == ("sudo ufw allow 47998,47999,48000,48002,48010/udp",)


def test_inactive_ufw_passes(make):
    system = make({"ufw status": ok(fixture("ufw_inactive.txt"))})
    assert check_firewall(system)[0].status is Status.PASS


def test_ufw_needing_root_is_skipped_with_a_hint_not_guessed(make):
    system = make({"ufw status": fail("ERROR: You need to be root to run this script")})
    [result] = check_firewall(system)
    assert result.status is Status.SKIP
    assert "sudo" in result.fix[0]


def test_parse_firewalld_ports():
    rules = parse_firewalld_ports("47984/tcp 47998-48000/udp junk\n")
    assert rules == [("tcp", 47984, 47984), ("udp", 47998, 48000)]


def test_firewalld_missing_ports_fails_with_add_port_commands(make):
    system = make({
        "firewall-cmd --state": ok("running\n"),
        "firewall-cmd --list-ports": ok("47984/tcp 47989/tcp 48010/tcp\n"),
    })
    [result] = check_firewall(system)
    assert result.status is Status.FAIL
    assert "--add-port=47998/udp" in result.fix[0]
    assert result.fix[1] == "sudo firewall-cmd --reload"


def test_no_known_firewall_is_skipped(make):
    assert check_firewall(make({}))[0].status is Status.SKIP
