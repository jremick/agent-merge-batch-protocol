# Approach

## Operating Model

Use a queue with one owner for `main`.

```text
worker PRs -> ready queue -> compatibility filter -> integration batch -> CI -> protected main -> deploy newest green
```

Workers can run in parallel. Merge writes cannot.

## Batch Algorithm

1. Read ready PRs ordered by ready time, then PR number.
2. Exclude PRs that are not independently reversible, lack required checks, depend on undeclared work, or require a serial deploy.
3. Build a batch up to the current batch limit.
4. Create a synthetic integration branch or merge group from current protected base.
5. Apply PRs in stable order.
6. Run the required integration checks once.
7. If green, merge the batch through the protected path.
8. If red, split the batch into halves and test subsets.
9. Continue splitting until passing subsets land and bad PRs are quarantined.
10. Deploy only the newest eligible green `main` commit.

## Batch Sizing

For the reference scenario, batch 8 is enough for 5-8 clean PRs with 2 minute CI.

For 16-40 PRs, batch size and CI capacity become first-order design parameters:

- batch 8 lands 16 clean PRs in 4m 32s;
- batch 8 lands 40 clean PRs in 11m 20s, which misses a 10 minute target;
- batch 16 lands 40 clean PRs in 7m 20s;
- one bad PR in a large batch can push elapsed time past target unless admission checks and split capacity are strong.

## Compatibility Rules

Batched PRs should be safe to deploy together and individually reversible.

Prefer:

- additive schema changes;
- backward-compatible API changes;
- feature flags for risky behavior;
- idempotent migrations;
- small independent touch sets.

Exclude from normal batches:

- destructive migrations;
- required manual operations;
- environment or credential changes;
- changes that must deploy before or after another PR;
- global locks or deployment steps that cannot be coalesced.

## Deployment Rule

Do not make every PR deployment a required pre-merge status check unless that is deliberately required. Most agent PRs should prove merge safety first, then let production deploy the newest green `main` commit under one environment lease.
