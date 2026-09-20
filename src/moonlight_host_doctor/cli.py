"""Command line entry point."""

from __future__ import annotations

import argparse
import json
import sys

from . import checks  # noqa: F401  (registers the checks)
from .model import CHECKS, Result, Status
from .system import System

LABELS = {
    Status.PASS: "[ OK ]",
    Status.WARN: "[WARN]",
    Status.FAIL: "[FAIL]",
    Status.SKIP: "[SKIP]",
}


def run_checks(system: System, only: list[str] | None = None) -> list[Result]:
    results: list[Result] = []
    for check_id, fn in CHECKS.items():
        if only and check_id not in only:
            continue
        try:
            results.extend(fn(system))
        except Exception as error:  # a broken check must not hide the others
            results.append(
                Result(check_id, check_id, Status.WARN, f"The check crashed: {error!r}. This is a bug in moonlight-host-doctor.")
            )
    return results


def format_text(results: list[Result]) -> str:
    lines = []
    for result in results:
        lines.append(f"{LABELS[result.status]} {result.title}: {result.detail}")
        lines.extend(f"       fix: {step}" for step in result.fix)
    counts = {s: sum(r.status is s for r in results) for s in Status}
    lines.append("")
    lines.append(
        f"{counts[Status.PASS]} ok, {counts[Status.WARN]} warnings, "
        f"{counts[Status.FAIL]} failed, {counts[Status.SKIP]} skipped"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None, system: System | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="moonlight-host-doctor",
        description="Read-only checks for a Sunshine game-streaming host. It prints fix "
        "commands but never runs them.",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--only", action="append", metavar="CHECK", help="run only this check (repeatable)")
    parser.add_argument("--list", action="store_true", help="list check names and exit")
    args = parser.parse_args(argv)

    if args.list:
        print("\n".join(CHECKS))
        return 0
    unknown = [c for c in args.only or [] if c not in CHECKS]
    if unknown:
        parser.error(f"unknown check: {', '.join(unknown)} (see --list)")

    results = run_checks(system or System(), args.only)
    if args.json:
        print(json.dumps([r.as_dict() for r in results], indent=2))
    else:
        print(format_text(results))
    return 1 if any(r.status is Status.FAIL for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
