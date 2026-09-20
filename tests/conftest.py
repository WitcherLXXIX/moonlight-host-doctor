from __future__ import annotations

from pathlib import Path

import pytest

from moonlight_host_doctor.system import CommandResult, System

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


class FakeSystem(System):
    """Answers from a table. A command that is not in it counts as not installed."""

    def __init__(self, commands=None, paths=(), dirs=None, root=False):
        # Keys are strings split on spaces, or tuples when an argument contains one.
        self.commands = {
            tuple(k.split()) if isinstance(k, str) else tuple(k): v
            for k, v in (commands or {}).items()
        }
        self.paths = set(paths)
        self.dirs = dirs or {}
        self.root = root

    def run(self, argv, timeout=5.0):
        return self.commands.get(tuple(argv))

    def has_command(self, name):
        return any(argv[0] == name for argv in self.commands)

    def list_dir(self, path):
        return self.dirs.get(path, [])

    def path_exists(self, path):
        return path in self.paths

    def is_root(self):
        return self.root


def ok(stdout: str) -> CommandResult:
    return CommandResult(0, stdout)


def fail(stderr: str = "", code: int = 1) -> CommandResult:
    return CommandResult(code, "", stderr)


@pytest.fixture
def make():
    return FakeSystem
