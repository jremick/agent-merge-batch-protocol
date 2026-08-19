# Apply Safely

Use this guide when applying the protocol to a real repository.

Before starting, confirm that the work actually arrives as independently reviewable PRs. If agents report to one parent task or edit one shared working tree, use parent-owned integration and disjoint file ownership instead of this protocol.

## 1. Inventory The Current Write Path

Capture without exposing secrets:

```text
DEFAULT_BRANCH:
BRANCH_PROTECTION:
REQUIRED_CHECKS:
MERGE_QUEUE_ENABLED:
CI_EVENTS:
DEPLOYMENT_WORKFLOW:
DEPLOYMENT_CONCURRENCY:
CAN_DEPLOY_BE_COALESCED:
```

Do not paste token output, environment variables, private URLs, raw headers, or local absolute paths into issues or docs.

## 2. Choose The Queue Layer

Use the smallest reliable queue that the repository can support:

| Context | Likely choice |
| --- | --- |
| GitHub merge queue is available for the repository's ownership and plan context | Start there, then add `merge_group` CI. |
| Team already uses Graphite | Use Graphite merge queue. |
| Need explicit batch merge semantics | Evaluate Mergify batch queue. |
| None are available | Use a custom coordinator with temporary integration branches and protected base writes. |

## 3. Fix CI Events

For GitHub merge queue, required workflows must include `merge_group`.

```yaml
on:
  pull_request:
  merge_group:
```

Avoid one global PR validation lock. A PR check concurrency key should distinguish PRs or merge groups.

## 4. Separate Deploy From Merge Validation

Production deploys should be serialized by environment, not by PR merge attempt.

```yaml
concurrency:
  group: production
  cancel-in-progress: false
```

When safe for the product, coalesce pending deploys and deploy the newest eligible green `main` SHA after the active deployment finishes.

## 5. Install Agent Rules

Add or adapt [the agent instruction template](../examples/agent-instructions.md).

The key rule is simple: workers open PRs and request merge; only the queue or coordinator merges.

## 6. Dry-Run Before Production

Minimum validation:

```bash
python3 tests/merge_benchmark.py --prs 8 --ci-seconds 120 --target-seconds 600 --batch-size 8 --parallel-split
python3 tests/git_batch_proof.py --prs 8 --ci-seconds 120 --parallel-split
python3 tests/git_batch_proof.py --prs 8 --bad-prs 5 --ci-seconds 120 --parallel-split
python3 scripts/scan_public_safety.py .
```

For a real repository proof:

1. use a throwaway repository or isolated clone;
2. create harmless synthetic branches;
3. run the real required test command;
4. inject one intentionally failing branch;
5. verify passing subsets land and the bad branch is quarantined;
6. delete scratch branches and temporary clones.

## 7. Stop Rules

Stop rollout if:

- direct writes to `main` are still possible;
- required checks do not run on merge groups or integration branches;
- deployment is a required PR check and cannot be coalesced;
- a batch includes irreversible or serial-only changes;
- logs or outputs would expose private data;
- flaky checks cause repeated queue churn.

## 8. Rollout Measures

Track:

- PRs merged per hour;
- queue wait time;
- CI runs per landed PR;
- stale branch retries;
- batch failure rate;
- isolated bad PR count;
- deployment queue age;
- revert rate after batched merges.
