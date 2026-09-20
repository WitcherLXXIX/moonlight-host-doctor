from conftest import fail, fixture, ok

from sunshine_doctor.checks.service import check_service, parse_units
from sunshine_doctor.model import Status

LIST = "systemctl --user list-units --type=service --all --plain --no-legend --no-pager"


def test_parse_units_reads_real_output():
    units = parse_units(fixture("systemctl_user_sunshine_running.txt"))
    sunshine = [u for u in units if "sunshine" in u.name.lower()]
    assert [(u.name, u.active, u.sub) for u in sunshine] == [
        ("app-dev.lizardbyte.app.Sunshine.service", "active", "running")
    ]


def test_running_service_passes_even_with_a_packaging_specific_name(make):
    system = make({LIST: ok(fixture("systemctl_user_sunshine_running.txt"))})
    [result] = check_service(system)
    assert result.status is Status.PASS
    assert "app-dev.lizardbyte.app.Sunshine.service" in result.detail


def test_stopped_service_fails_and_names_the_unit_in_the_fix(make):
    stopped = "sunshine.service loaded inactive dead Sunshine\n"
    [result] = check_service(make({LIST: ok(stopped)}))
    assert result.status is Status.FAIL
    assert "systemctl --user enable --now sunshine.service" in result.fix


def test_installed_without_a_user_service_warns(make):
    system = make({LIST: ok(""), "sunshine --version": ok("x")})
    [result] = check_service(system)
    assert result.status is Status.WARN


def test_not_installed_fails(make):
    [result] = check_service(make({LIST: ok("pipewire.service loaded active running x\n")}))
    assert result.status is Status.FAIL


def test_no_systemd_is_skipped_not_failed(make):
    assert check_service(make({LIST: fail()}))[0].status is Status.SKIP
    assert check_service(make({}))[0].status is Status.SKIP
