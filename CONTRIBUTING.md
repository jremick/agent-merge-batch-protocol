# Contributing

This repository is a public research and validation artifact. Contributions should improve clarity, reproducibility, or safety.

## Ground Rules

- Keep examples generic.
- Do not add credentials, `.env` files, auth output, local absolute paths, private hostnames, raw social exports, customer data, or production identifiers.
- Do not add screenshots unless they are intentionally public and scrubbed.
- Keep claims tied to a reproducible command, public source, or clearly marked assumption.

## Before Opening A PR

```bash
python3 tests/merge_benchmark.py --prs 8 --ci-seconds 120 --target-seconds 600 --batch-size 8 --parallel-split
python3 tests/git_batch_proof.py --prs 8 --ci-seconds 120 --parallel-split
python3 scripts/scan_public_safety.py .
git diff --check
```

## PR Description Checklist

- What changed?
- Which scenario does it affect?
- What validation was run?
- Does the change alter public-safety behavior?
