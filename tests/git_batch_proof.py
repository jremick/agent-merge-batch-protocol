#!/usr/bin/env python3
"""Local Git proof for batch merge coordination.

This creates a temporary repository, synthesizes PR branches, merges compatible
branches into integration branches, validates the integration result, and then
advances `main`. It does not touch any remote repository.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProofResult:
    merged: int
    failed: int
    ci_runs: int
    modeled_elapsed_s: float

    @property
    def merges_per_minute(self) -> float:
        if self.modeled_elapsed_s <= 0:
            return 0.0
        return self.merged / (self.modeled_elapsed_s / 60.0)


def run(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def init_repo(path: Path, prs: int, bad_prs: set[int]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    run(["git", "init", "-b", "main"], path)
    run(["git", "config", "user.email", "agent-merge-proof@example.invalid"], path)
    run(["git", "config", "user.name", "Agent Merge Proof"], path)
    (path / "README.md").write_text("# merge proof\n", encoding="utf-8")
    run(["git", "add", "README.md"], path)
    run(["git", "commit", "-m", "initial"], path)

    for pr in range(1, prs + 1):
        run(["git", "checkout", "-B", f"pr-{pr}", "main"], path)
        feature = path / "features" / f"feature-{pr}.txt"
        feature.parent.mkdir(exist_ok=True)
        feature.write_text(f"feature {pr}\n", encoding="utf-8")
        if pr in bad_prs:
            (path / "features" / f"FAIL-{pr}.txt").write_text("fail\n", encoding="utf-8")
        run(["git", "add", "features"], path)
        run(["git", "commit", "-m", f"pr {pr}"], path)

    run(["git", "checkout", "main"], path)


def integration_valid(path: Path) -> bool:
    feature_dir = path / "features"
    fail_files = list(feature_dir.glob("FAIL-*.txt")) if feature_dir.exists() else []
    if fail_files:
        return False
    run(["git", "diff", "--check"], path)
    return True


def try_group(
    path: Path,
    branches: list[str],
    ci_seconds: float,
    merge_overhead_seconds: float,
    parallel_split: bool,
    attempt: int,
) -> tuple[int, int, int, float]:
    branch_name = f"integration-{attempt}-{'-'.join(branches)}"
    run(["git", "checkout", "-B", branch_name, "main"], path)

    merge_ok = True
    for branch in branches:
        result = run(["git", "merge", "--no-ff", "--no-edit", branch], path, check=False)
        if result.returncode != 0:
            run(["git", "merge", "--abort"], path, check=False)
            merge_ok = False
            break

    ci_runs = 1
    if merge_ok and integration_valid(path):
        run(["git", "checkout", "main"], path)
        run(["git", "merge", "--ff-only", branch_name], path)
        elapsed = ci_seconds + (len(branches) * merge_overhead_seconds)
        return len(branches), 0, ci_runs, elapsed

    run(["git", "checkout", "main"], path)
    run(["git", "branch", "-D", branch_name], path, check=False)

    if len(branches) == 1:
        return 0, 1, ci_runs, ci_seconds

    midpoint = len(branches) // 2
    left = try_group(
        path,
        branches[:midpoint],
        ci_seconds,
        merge_overhead_seconds,
        parallel_split,
        attempt + 1,
    )
    right = try_group(
        path,
        branches[midpoint:],
        ci_seconds,
        merge_overhead_seconds,
        parallel_split,
        attempt + 1000,
    )
    split_elapsed = max(left[3], right[3]) if parallel_split else left[3] + right[3]
    return (
        left[0] + right[0],
        left[1] + right[1],
        ci_runs + left[2] + right[2],
        ci_seconds + split_elapsed,
    )


def parse_bad_prs(value: str) -> set[int]:
    if not value:
        return set()
    return {int(item.strip()) for item in value.split(",") if item.strip()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prs", type=int, default=8)
    parser.add_argument("--bad-prs", default="")
    parser.add_argument("--ci-seconds", type=float, default=120.0)
    parser.add_argument("--merge-overhead-seconds", type=float, default=2.0)
    parser.add_argument("--parallel-split", action="store_true")
    parser.add_argument("--keep-repo", action="store_true")
    args = parser.parse_args()

    repo_path = Path(tempfile.mkdtemp(prefix="agent-merge-proof-"))
    try:
        init_repo(repo_path, args.prs, parse_bad_prs(args.bad_prs))
        branches = [f"pr-{pr}" for pr in range(1, args.prs + 1)]
        merged, failed, ci_runs, modeled_elapsed_s = try_group(
            repo_path,
            branches,
            args.ci_seconds,
            args.merge_overhead_seconds,
            args.parallel_split,
            1,
        )
        result = ProofResult(merged, failed, ci_runs, modeled_elapsed_s)
        print(f"merged: {result.merged}")
        print(f"failed: {result.failed}")
        print(f"ci_runs: {result.ci_runs}")
        print(f"modeled_elapsed_s: {result.modeled_elapsed_s:.1f}")
        print(f"merges_per_minute: {result.merges_per_minute:.2f}")
        print(f"main_commits: {run(['git', 'rev-list', '--count', 'main'], repo_path).stdout.strip()}")
        print("target_10m:", "PASS" if result.modeled_elapsed_s <= 600 else "FAIL")
        if args.keep_repo:
            print("temp_repo_retained: yes")
    finally:
        if not args.keep_repo:
            shutil.rmtree(repo_path)


if __name__ == "__main__":
    main()
