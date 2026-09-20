"""Result types and the check registry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from .system import System


class Status(str, Enum):
    PASS = "pass"
    INFO = "info"  # a fact worth explaining that is not a problem
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"  # could not be determined here, for example a command needs root


@dataclass(frozen=True)
class Result:
    check: str
    title: str
    status: Status
    detail: str = ""
    fix: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict:
        return {
            "check": self.check,
            "title": self.title,
            "status": self.status.value,
            "detail": self.detail,
            "fix": list(self.fix),
        }


CheckFn = Callable[[System], list[Result]]
CHECKS: dict[str, CheckFn] = {}


def check(check_id: str) -> Callable[[CheckFn], CheckFn]:
    """Register a check. Order of registration is the order they run in."""

    def register(fn: CheckFn) -> CheckFn:
        CHECKS[check_id] = fn
        return fn

    return register
