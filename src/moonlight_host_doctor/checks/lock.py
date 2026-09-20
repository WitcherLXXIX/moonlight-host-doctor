"""Will a woken or idle machine show a lock screen to the Moonlight client?

Informational only: locking is a valid, often safer, choice. A stream that starts while
the screen is locked shows the lock screen, and the password is typed on the client.
Only KDE Plasma is read so far.
"""

from __future__ import annotations

from ..model import Result, Status, check
from ..system import System

ID = "lock"
TITLE = "Screen lock"


def _read(system: System, key: str, default: str) -> str | None:
    shown = system.run([
        "kreadconfig6", "--file", "kscreenlockerrc", "--group", "Daemon",
        "--key", key, "--default", default,
    ])
    if shown is None or shown.returncode != 0:
        return None
    return shown.stdout.strip().lower() or None


@check(ID)
def check_lock(system: System) -> list[Result]:
    if not system.has_command("kreadconfig6"):
        return [Result(ID, TITLE, Status.SKIP, "Screen-lock settings are only read for KDE Plasma so far.")]

    # KDE's own defaults apply when a key is unset: lock on resume, lock after 5 idle minutes.
    on_resume = _read(system, "LockOnResume", "true")
    auto = _read(system, "Autolock", "true")
    minutes = _read(system, "Timeout", "5")
    if on_resume is None or auto is None:
        return [Result(ID, TITLE, Status.SKIP, "Could not read the KDE screen-lock settings.")]

    notes = []
    if on_resume == "true":
        notes.append("The screen locks when the PC wakes from sleep, so waking it with Moonlight "
                     "shows the lock screen and you type your password on the client.")
    if auto == "true":
        notes.append(f"It also locks after {minutes or '5'} idle minutes, and a stream started then "
                     "shows the lock screen.")
    if not notes:
        return [Result(ID, TITLE, Status.INFO,
                       "Automatic locking is off: waking or streaming lands on your desktop. "
                       "Anyone who can reach the machine can then use it.")]
    return [Result(
        ID, TITLE, Status.INFO, " ".join(notes),
        ("To skip the lock after waking (a security tradeoff, only for a machine you control physically): "
         "kwriteconfig6 --file kscreenlockerrc --group Daemon --key LockOnResume false",)
        if on_resume == "true" else (),
    )]
