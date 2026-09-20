import json

import pytest
from conftest import fail, fixture, ok

from moonlight_host_doctor.cli import main, run_checks
from moonlight_host_doctor.model import CHECKS, Status


def test_all_checks_are_registered_in_running_order():
    assert list(CHECKS) == ["service", "listening", "firewall", "wol", "tailscale"]


def test_a_crashing_check_becomes_a_warning_and_does_not_hide_the_others(make, monkeypatch):
    def boom(system):
        raise RuntimeError("bad parse")

    monkeypatch.setitem(CHECKS, "service", boom)
    results = run_checks(make({}))
    assert results[0].status is Status.WARN and "bad parse" in results[0].detail
    assert {r.check for r in results} >= {"listening", "firewall", "wol", "tailscale"}


def test_exit_code_is_1_only_when_something_failed(make, capsys):
    assert main(["--only", "firewall"], system=make({})) == 0  # skipped, not failed
    system = make({"ss -H -tln": ok("")})
    assert main(["--only", "listening"], system=system) == 1


def test_json_output_is_parseable(make, capsys):
    main(["--json", "--only", "firewall"], system=make({}))
    data = json.loads(capsys.readouterr().out)
    assert data[0]["check"] == "firewall" and data[0]["status"] == "skip"


def test_unknown_check_name_is_rejected(make):
    with pytest.raises(SystemExit):
        main(["--only", "nope"], system=make({}))


def test_the_tool_never_runs_a_command_that_changes_anything(make):
    """Every command a check issues must be read-only."""
    issued = []

    class Recording(type(make({}))):
        """Pretends every tool and a wired NIC exist, so every code path issues its commands."""

        def run(self, argv, timeout=5.0):
            issued.append(argv)
            return ok("running\n")

        def has_command(self, name):
            return True

        def list_dir(self, path):
            return ["enp6s0"]

        def path_exists(self, path):
            return path.endswith("/device")

    run_checks(Recording())
    forbidden = {"enable", "start", "stop", "restart", "add", "modify", "allow", "delete", "-s", "up", "down", "login", "set"}
    assert issued, "checks should have issued commands"
    for argv in issued:
        assert not forbidden & set(argv[1:]), argv


def test_version_flag_prints_the_package_version(capsys):
    from moonlight_host_doctor import __version__

    with pytest.raises(SystemExit) as stop:
        main(["--version"])
    assert stop.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_root_hints_use_a_command_that_sudo_can_find(make):
    """A user-level install lives outside sudo's PATH, so the hint must pass PATH through."""
    system = make(
        {
            "ufw status": fail("ERROR: You need to be root"),
            "ethtool enp6s0": ok(fixture("ethtool_unprivileged.txt")),
            "tailscale status --json": ok(fixture("tailscale_status_healthy.json")),
            ("getent", "hosts", "linux.tail-example.ts.net"): ok(fixture("getent_tailscale_name.txt")),
        },
        paths={"/sys/class/net/enp6s0/device"},
        dirs={"/sys/class/net": ["enp6s0"]},
    )
    hints = [step for r in run_checks(system) for step in r.fix if step.startswith("sudo")]
    assert len(hints) == 3  # firewall, wol and the tailscale firewall check
    assert all(step.startswith('sudo env "PATH=$PATH" moonlight-host-doctor --only ') for step in hints)
