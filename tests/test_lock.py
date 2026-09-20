from conftest import fail, fixture, ok

from moonlight_host_doctor.checks.lock import check_lock
from moonlight_host_doctor.model import Status


def key(name, default):
    return ("kreadconfig6", "--file", "kscreenlockerrc", "--group", "Daemon", "--key", name, "--default", default)


def machine(make, on_resume, auto, timeout="kreadconfig_timeout_5.txt"):
    return make({
        key("LockOnResume", "true"): ok(fixture(on_resume)),
        key("Autolock", "true"): ok(fixture(auto)),
        key("Timeout", "5"): ok(fixture(timeout)),
    })


def test_the_real_machine_with_locking_off_reports_that_the_desktop_is_open(make):
    [result] = check_lock(machine(make, "kreadconfig_false.txt", "kreadconfig_false.txt"))
    assert result.status is Status.INFO
    assert "lands on your desktop" in result.detail and result.fix == ()


def test_lock_on_resume_explains_the_lock_screen_and_offers_an_opt_out(make):
    [result] = check_lock(machine(make, "kreadconfig_true.txt", "kreadconfig_false.txt"))
    assert result.status is Status.INFO
    assert "wakes from sleep" in result.detail
    assert "LockOnResume false" in result.fix[0] and "security tradeoff" in result.fix[0]


def test_idle_autolock_mentions_the_timeout_and_offers_no_fix_when_resume_is_unlocked(make):
    [result] = check_lock(machine(make, "kreadconfig_false.txt", "kreadconfig_true.txt"))
    assert "5 idle minutes" in result.detail
    assert result.fix == ()


def test_an_unset_key_uses_kdes_own_defaults_in_the_command(make):
    system = make({})
    assert check_lock(system)[0].status is Status.SKIP  # no kreadconfig6: not KDE
    unreadable = make({key("LockOnResume", "true"): fail(), key("Autolock", "true"): ok("true\n")})
    assert check_lock(unreadable)[0].status is Status.SKIP


def test_it_is_informational_and_never_fails_the_run(make, capsys):
    from moonlight_host_doctor.cli import main

    system = machine(make, "kreadconfig_true.txt", "kreadconfig_true.txt")
    assert main(["--only", "lock"], system=system) == 0
    assert "[INFO]" in capsys.readouterr().out
