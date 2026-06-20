#!/usr/bin/env python3
"""Benchmark merge/deploy coordination policies for parallel coding agents."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Metrics:
    policy: str
    prs: int
    merged: int
    failed: int
    elapsed_s: float
    ci_runs: int
    stale_retries: int

    @property
    def merges_per_minute(self) -> float:
        if self.elapsed_s <= 0:
            return 0.0
        return self.merged / (self.elapsed_s / 60.0)


def simulate_naive_parallel(
    prs: int,
    ci_seconds: float,
    merge_overhead_seconds: float,
    stale_retry_penalty_seconds: float,
) -> Metrics:
    elapsed = 0.0
    remaining = prs
    ci_runs = 0
    stale_retries = 0
    merged = 0

    while remaining > 0:
        ci_runs += remaining
        elapsed += ci_seconds + merge_overhead_seconds
        merged += 1
        remaining -= 1
        stale_retries += remaining
        if remaining:
            elapsed += stale_retry_penalty_seconds

    return Metrics(
        policy="naive-parallel-deploy",
        prs=prs,
        merged=merged,
        failed=0,
        elapsed_s=elapsed,
        ci_runs=ci_runs,
        stale_retries=stale_retries,
    )


def simulate_serial_coordinator(
    prs: int,
    ci_seconds: float,
    merge_overhead_seconds: float,
) -> Metrics:
    return Metrics(
        policy="serial-merge-agent",
        prs=prs,
        merged=prs,
        failed=0,
        elapsed_s=prs * (ci_seconds + merge_overhead_seconds),
        ci_runs=prs,
        stale_retries=0,
    )


def _batch_cost(
    batch_size: int,
    bad_prs: set[int],
    start_pr: int,
    ci_seconds: float,
    merge_overhead_seconds: float,
    parallel_split: bool,
) -> tuple[float, int, int, int]:
    batch = list(range(start_pr, start_pr + batch_size))
    elapsed = ci_seconds
    ci_runs = 1

    if not any(pr in bad_prs for pr in batch):
        elapsed += batch_size * merge_overhead_seconds
        return elapsed, ci_runs, batch_size, 0

    if batch_size == 1:
        return elapsed, ci_runs, 0, 1

    left_size = batch_size // 2
    right_size = batch_size - left_size
    left = _batch_cost(
        left_size,
        bad_prs,
        start_pr,
        ci_seconds,
        merge_overhead_seconds,
        parallel_split,
    )
    right = _batch_cost(
        right_size,
        bad_prs,
        start_pr + left_size,
        ci_seconds,
        merge_overhead_seconds,
        parallel_split,
    )
    split_elapsed = max(left[0], right[0]) if parallel_split else left[0] + right[0]
    return (
        elapsed + split_elapsed,
        ci_runs + left[1] + right[1],
        left[2] + right[2],
        left[3] + right[3],
    )


def simulate_batched_queue(
    prs: int,
    ci_seconds: float,
    merge_overhead_seconds: float,
    batch_size: int,
    bad_prs: set[int],
    parallel_split: bool,
) -> Metrics:
    elapsed = 0.0
    ci_runs = 0
    merged = 0
    failed = 0
    cursor = 1

    while cursor <= prs:
        current_batch_size = min(batch_size, prs - cursor + 1)
        cost = _batch_cost(
            current_batch_size,
            bad_prs,
            cursor,
            ci_seconds,
            merge_overhead_seconds,
            parallel_split,
        )
        elapsed += cost[0]
        ci_runs += cost[1]
        merged += cost[2]
        failed += cost[3]
        cursor += current_batch_size

    return Metrics(
        policy=f"batched-queue-{batch_size}{'-parallel-split' if parallel_split else ''}",
        prs=prs,
        merged=merged,
        failed=failed,
        elapsed_s=elapsed,
        ci_runs=ci_runs,
        stale_retries=0,
    )


def max_prs_under(
    simulator: Callable[[int], Metrics],
    target_seconds: float,
    ceiling: int,
) -> int:
    max_ok = 0
    for prs in range(1, ceiling + 1):
        if simulator(prs).elapsed_s <= target_seconds:
            max_ok = prs
        else:
            break
    return max_ok


def format_seconds(seconds: float) -> str:
    minutes = int(seconds // 60)
    remainder = seconds - (minutes * 60)
    if minutes:
        return f"{minutes}m {remainder:.1f}s"
    return f"{remainder:.1f}s"


def parse_bad_prs(value: str) -> set[int]:
    if not value:
        return set()
    return {int(item.strip()) for item in value.split(",") if item.strip()}


def print_table(metrics: list[Metrics], target_seconds: float) -> None:
    headers = [
        "policy",
        "merged",
        "failed",
        "elapsed",
        "ci_runs",
        "stale_retries",
        "merges/min",
        "target",
    ]
    rows = [
        [
            item.policy,
            str(item.merged),
            str(item.failed),
            format_seconds(item.elapsed_s),
            str(item.ci_runs),
            str(item.stale_retries),
            f"{item.merges_per_minute:.2f}",
            "PASS" if item.elapsed_s <= target_seconds else "FAIL",
        ]
        for item in metrics
    ]
    widths = [
        max(len(row[index]) for row in rows + [headers])
        for index in range(len(headers))
    ]
    print(" | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prs", type=int, default=8)
    parser.add_argument("--ci-seconds", type=float, default=120.0)
    parser.add_argument("--merge-overhead-seconds", type=float, default=2.0)
    parser.add_argument("--stale-retry-penalty-seconds", type=float, default=480.0)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--target-seconds", type=float, default=600.0)
    parser.add_argument("--bad-prs", default="")
    parser.add_argument("--parallel-split", action="store_true")
    parser.add_argument("--rate-ceiling", type=int, default=60)
    args = parser.parse_args()

    bad_prs = parse_bad_prs(args.bad_prs)
    metrics = [
        simulate_naive_parallel(
            args.prs,
            args.ci_seconds,
            args.merge_overhead_seconds,
            args.stale_retry_penalty_seconds,
        ),
        simulate_serial_coordinator(
            args.prs,
            args.ci_seconds,
            args.merge_overhead_seconds,
        ),
        simulate_batched_queue(
            args.prs,
            args.ci_seconds,
            args.merge_overhead_seconds,
            args.batch_size,
            bad_prs,
            args.parallel_split,
        ),
    ]

    print(
        "Scenario: "
        f"{args.prs} ready PRs, CI={format_seconds(args.ci_seconds)}, "
        f"target={format_seconds(args.target_seconds)}, "
        f"bad_prs={sorted(bad_prs) or 'none'}"
    )
    print_table(metrics, args.target_seconds)
    print()
    print("Rate limit under target:")
    for label, simulator in [
        (
            "naive-parallel-deploy",
            lambda prs: simulate_naive_parallel(
                prs,
                args.ci_seconds,
                args.merge_overhead_seconds,
                args.stale_retry_penalty_seconds,
            ),
        ),
        (
            "serial-merge-agent",
            lambda prs: simulate_serial_coordinator(
                prs,
                args.ci_seconds,
                args.merge_overhead_seconds,
            ),
        ),
        (
            f"batched-queue-{args.batch_size}",
            lambda prs: simulate_batched_queue(
                prs,
                args.ci_seconds,
                args.merge_overhead_seconds,
                args.batch_size,
                set(),
                args.parallel_split,
            ),
        ),
    ]:
        print(
            f"- {label}: "
            f"{max_prs_under(simulator, args.target_seconds, args.rate_ceiling)} PRs "
            f"in <= {format_seconds(args.target_seconds)}"
        )


if __name__ == "__main__":
    main()
