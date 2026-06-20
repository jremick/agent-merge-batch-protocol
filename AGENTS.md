# AGENTS.md

Version: 1.0.0
Last updated: 2026-06-20

Purpose: guide agents applying this repository's merge-batch protocol without leaking private data or bypassing protected branches.

## Safety Boundary

- Do not commit secrets, `.env` files, auth output, raw logs, local absolute paths, screenshots with private data, or production identifiers.
- Do not push directly to `main`.
- Do not disable branch protection, required checks, vulnerability alerts, or secret scanning to make a demo pass.
- Do not run production deploys as part of a local proof.
- Use throwaway repositories, isolated clones, or temporary integration branches for validation.

## Worker Agents

Workers implement one PR and stop at a structured merge request.

```text
MERGE_REQUEST:
PR:
BASE_SHA:
HEAD_SHA:
TOUCH_SET:
CHECKS:
COMPATIBILITY:
DEPLOYMENT_MODE: COALESCIBLE | SERIAL
DEPENDS_ON:
RISK: LOW | MEDIUM | HIGH
ROLLBACK:
```

Rules:

1. Branch from current protected base.
2. Keep changes independently reversible.
3. Run the repository's focused checks.
4. Open or update the PR.
5. Post the merge request block.
6. Stop. The worker must not merge, deploy, rebase in a loop, or fight the queue.

## Merge Coordinator Agents

The coordinator owns the write path to `main`.

Rules:

1. Build a queue from ready PRs.
2. Reject PRs with missing checks, unresolved reviews, unclear rollback, undeclared dependencies, or serial-only deployment requirements.
3. Batch compatible PRs up to the configured batch limit.
4. Validate the synthetic integration branch or merge group.
5. Merge only through the protected path.
6. Split failing batches until the bad PR is isolated.
7. Quarantine bad PRs with evidence and continue with passing subsets.
8. Post the final state for every queued PR.

## Required Checks Before Applying

- Confirm branch protection prevents direct writes to `main`.
- Confirm CI runs on the exact commit or merge group that would enter `main`.
- Confirm deployment has a separate concurrency gate from PR validation.
- Confirm the public-safety scanner passes before publishing any docs or outputs.
- Confirm benchmark assumptions match the real repo's CI duration and runner capacity.

## Stop Conditions

Stop and ask for a human decision if:

- the repo cannot prevent direct writes to `main`;
- required checks do not run on merge groups or integration branches;
- a batch includes destructive migrations, irreversible data changes, or serial deployment work;
- validation would require exposing private data or credentials;
- the queue repeatedly isolates the same flaky check without a clear owner.
