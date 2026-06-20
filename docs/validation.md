# Validation

This repository includes two local validation styles:

1. deterministic event modeling;
2. an actual local Git proof that creates synthetic PR branches and batch-merges them through an integration branch.

No remote repository is mutated by these scripts.

## Deterministic Benchmark

```bash
python3 tests/merge_benchmark.py --prs 8 --ci-seconds 120 --target-seconds 600 --batch-size 8 --parallel-split
```

Expected result:

| Policy | Elapsed | CI runs | Stale retries | Target |
| --- | ---: | ---: | ---: | --- |
| Naive parallel deploy | 72m 16s | 36 | 28 | fail |
| Serial merge agent | 16m 16s | 8 | 0 | fail |
| Batched queue | 2m 16s | 1 | 0 | pass |

## Local Git Proof

```bash
python3 tests/git_batch_proof.py --prs 8 --ci-seconds 120 --parallel-split
```

Expected result:

- 8 synthetic PR branches merged;
- 1 modeled CI run;
- 136 seconds modeled elapsed time;
- 10 minute target passes.

Bad PR isolation:

```bash
python3 tests/git_batch_proof.py --prs 8 --bad-prs 5 --ci-seconds 120 --parallel-split
```

Expected result:

- 7 PR branches merged;
- 1 bad branch isolated;
- 7 modeled CI runs;
- 482 seconds modeled elapsed time;
- 10 minute target passes.

## Real-Repo Validation Boundary

A real npm workspace application was used as an external validation case in an isolated clone. The validation ran the app's real web test command after creating synthetic PR branches.

Public-safe summary:

| Case | Result |
| --- | --- |
| 8 synthetic PR branches | 1 real integration test run; target passed |
| 5 synthetic PR branches with 1 injected bad branch | 4 good branches landed; 1 bad branch isolated; target passed |

The source path, scratch clone path, raw logs, and repository-specific internals are intentionally omitted from this public artifact.

## Scale Boundary

The model answers "would this scale to 16-40 PRs?" with a qualified yes:

- clean batches scale when batch size and CI capacity scale;
- failure isolation is the limiting factor;
- large batches need stronger admission checks, parallel split capacity, and a clear quarantine policy;
- 40 clean PRs miss a 10 minute target at batch 8 but pass at batch 16 under the model assumptions.
