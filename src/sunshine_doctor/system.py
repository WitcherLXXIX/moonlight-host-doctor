"""The only place checks touch the machine.

Every check reads system state through a `System`, so tests can hand it a fake
that returns saved command output and never needs real hardware.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str = ""


class System:
    def run(self, argv: list[str], timeout: float = 5.0) -> CommandResult | None:
        """Run a command. None means it is not installed or did not finish."""
        try:
            done = subprocess.run(
                argv, capture_output=True, text=True, timeout=timeout, check=False
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
            return None
        return CommandResult(done.returncode, done.stdout, done.stderr)

    def has_command(self, name: str) -> bool:
        return shutil.which(name) is not None

    def list_dir(self, path: str) -> list[str]:
        try:
            return sorted(os.listdir(path))
        except OSError:
            return []

    def path_exists(self, path: str) -> bool:
        return Path(path).exists()

    def is_root(self) -> bool:
        return os.geteuid() == 0
