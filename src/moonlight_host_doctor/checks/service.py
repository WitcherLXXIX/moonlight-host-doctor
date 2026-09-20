"""Is Sunshine installed and running as a user service?"""

from __future__ import annotations

from dataclasses import dataclass

from ..model import Result, Status, check
from ..system import System

ID = "service"
TITLE = "Sunshine service"


@dataclass(frozen=True)
class Unit:
    name: str
    load: str
    active: str
    sub: str


def parse_units(text: str) -> list[Unit]:
    """Parse `systemctl list-units --plain --no-legend` output."""
    units = []
    for line in text.splitlines():
        parts = line.split(None, 4)
        if len(parts) >= 4:
            units.append(Unit(parts[0], parts[1], parts[2], parts[3]))
    return units


@check(ID)
def check_service(system: System) -> list[Result]:
    if system.is_root():
        # `systemctl --user` would ask root's own session, not the user who runs Sunshine.
        return [
            Result(ID, TITLE, Status.SKIP,
                   "Running as root, which cannot see your user services. Run this check without sudo.",
                   ("moonlight-host-doctor --only service",))
        ]
    listed = system.run(
        [
            "systemctl", "--user", "list-units", "--type=service", "--all",
            "--plain", "--no-legend", "--no-pager",
        ]
    )
    if listed is None or listed.returncode != 0:
        return [Result(ID, TITLE, Status.SKIP, "systemctl --user is not available here.")]

    # The unit name differs between packages, for example
    # "app-dev.lizardbyte.app.Sunshine.service" on Arch, so match by substring.
    units = [u for u in parse_units(listed.stdout) if "sunshine" in u.name.lower()]

    if not units:
        if system.has_command("sunshine"):
            return [
                Result(
                    ID, TITLE, Status.WARN,
                    "Sunshine is installed but no user service was found, so it will "
                    "not start on login.",
                    ("systemctl --user enable --now sunshine",),
                )
            ]
        return [
            Result(
                ID, TITLE, Status.FAIL,
                "Sunshine was not found.",
                ("Install it: https://docs.lizardbyte.dev/projects/sunshine/latest/",),
            )
        ]

    running = [u for u in units if u.active == "active" and u.sub == "running"]
    if running:
        return [Result(ID, TITLE, Status.PASS, f"{running[0].name} is running.")]

    unit = units[0]
    return [
        Result(
            ID, TITLE, Status.FAIL,
            f"{unit.name} is {unit.active} ({unit.sub}).",
            (f"systemctl --user enable --now {unit.name}",
             f"journalctl --user -u {unit.name} -n 50"),
        )
    ]
