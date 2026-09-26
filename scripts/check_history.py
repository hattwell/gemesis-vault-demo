"""Inspect every Git tree in the new demo history before first publication."""
from __future__ import annotations

from pathlib import Path
import subprocess

from scripts.check_public_artifact import EXACT, FORBIDDEN, PREFIXES, private_name


def check_history(root: Path) -> list[tuple[str, str, str]]:
    problems: list[tuple[str, str, str]] = []
    commits = subprocess.check_output(["git", "rev-list", "--all"], cwd=root, text=True).splitlines()
    for commit in commits:
        short = commit[:8]
        paths = subprocess.check_output(["git", "ls-tree", "-rz", "--name-only", commit], cwd=root).split(b"\0")
        for item in filter(None, paths):
            path = item.decode("utf-8")
            if path not in EXACT and not path.startswith(PREFIXES):
                problems.append((short, path, "not-allowlisted"))
            if private_name(Path(path)):
                problems.append((short, path, "private-name"))
            contents = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=root)
            if len(contents) > 2_000_000:
                problems.append((short, path, "oversized"))
                continue
            if path == "app/public/gemesislogo.jpg":
                continue
            try:
                text = contents.decode("utf-8")
            except UnicodeDecodeError:
                problems.append((short, path, "unexpected-binary"))
                continue
            for rule, signature in FORBIDDEN.items():
                if signature in text:
                    problems.append((short, path, rule))
        message = subprocess.check_output(["git", "log", "-1", "--format=%B", commit], cwd=root, text=True)
        for rule, signature in FORBIDDEN.items():
            if signature in message:
                problems.append((short, "commit-message", rule))
    return problems


if __name__ == "__main__":
    issues = check_history(Path(__file__).resolve().parents[1])
    for commit, path, rule in issues:
        print(f"{commit} {path}: {rule}")
    if issues:
        raise SystemExit(1)
    print("New demo Git history: only approved fictional files and metadata.")
