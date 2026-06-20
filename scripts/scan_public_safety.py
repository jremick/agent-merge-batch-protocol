#!/usr/bin/env python3
"""Public-surface scanner for this repository.

The scanner intentionally reports file paths and rule names only. It does not
print matching line content, because the match may be sensitive.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "tmp",
    "work",
}

SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".zip",
}

ABSOLUTE_USER_PATH_PATTERN = (
    r"("
    + "/"
    + "Users/"
    + "|"
    + "/"
    + "home/"
    + "|"
    + "C:"
    + r"\\\\"
    + "Users"
    + r"\\\\"
    + r")"
)
GITHUB_TOKEN_PATTERN = (
    r"("
    + "|".join(
        [
            "gh" + "p_",
            "gh" + "o_",
            "gh" + "u_",
            "gh" + "s_",
            "gh" + "r_",
            "github" + "_pat_",
        ]
    )
    + r")"
)
RAW_X_EXPORT_PATTERN = (
    r"("
    + "source-"
    + "conversation"
    + "|"
    + "quoted-"
    + "conversation"
    + "|"
    + "x-"
    + "thread/"
    + r")"
)

RULES: list[tuple[str, re.Pattern[str]]] = [
    ("absolute-user-path", re.compile(ABSOLUTE_USER_PATH_PATTERN)),
    ("private-key", re.compile(r"BEGIN [A-Z ]*PRIVATE KEY")),
    ("github-token", re.compile(GITHUB_TOKEN_PATTERN)),
    ("openai-token-shape", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
    ("aws-access-key-shape", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("raw-x-export-reference", re.compile(RAW_X_EXPORT_PATTERN)),
    (
        "non-placeholder-email",
        re.compile(
            r"\\b[A-Za-z0-9._%+-]+@"
            r"(?!example\\.invalid\\b)"
            r"[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\\b"
        ),
    ),
]


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() not in SKIP_SUFFIXES:
            files.append(path)
    return sorted(files)


def scan(root: Path) -> list[tuple[Path, str]]:
    findings: list[tuple[Path, str]] = []
    for path in iter_files(root):
        relative = path.relative_to(root)
        path_text = str(relative)

        if re.search(r"(^|[/\\])\\.env(\\.|$)", path_text):
            findings.append((relative, "env-file-name"))
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            findings.append((relative, "read-error"))
            continue

        for rule_name, pattern in RULES:
            if pattern.search(path_text) or pattern.search(text):
                findings.append((relative, rule_name))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=".")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    findings = scan(root)
    if findings:
        print("Public-safety scan failed. Review these files and rules:")
        for path, rule in findings:
            print(f"- {path}: {rule}")
        return 1

    print("Public-safety scan passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
