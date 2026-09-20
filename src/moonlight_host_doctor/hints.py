"""Shared wording for fix hints."""

from __future__ import annotations


def sudo_rerun(*only: str) -> str:
    """A command that re-runs some checks as root.

    A plain `sudo moonlight-host-doctor` fails when the tool was installed for one user
    (pipx, pip --user), because sudo does not search that user's ~/.local/bin. Passing the
    caller's PATH through works in bash, zsh and fish.
    """
    flags = " ".join(f"--only {check}" for check in only)
    return f'sudo env "PATH=$PATH" moonlight-host-doctor {flags}'
