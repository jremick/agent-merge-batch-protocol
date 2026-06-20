# Agent Instructions Template

Copy and adapt this into a repository-specific `AGENTS.md`.

## Merge Policy

Workers never merge into `main`. Workers never run a deploy command that merges a PR.

Workers stop after opening a PR, running focused checks, and posting:

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

## Coordinator Policy

Only the merge coordinator or configured merge queue may advance `main`.

The coordinator must:

1. accept only ready PRs with current checks and clear rollback;
2. batch compatible `COALESCIBLE` PRs;
3. exclude `SERIAL` PRs from normal batches;
4. validate a synthetic integration branch or merge group;
5. merge through branch protection;
6. split failing batches;
7. quarantine bad PRs with evidence;
8. post final state for every queued PR.

## Required Repository Contract

- `main` is protected.
- CI validates the exact integration commit or merge group.
- Production deploy is separate from PR validation.
- Agents cannot bypass the queue.
- Secrets and local machine details are never pasted into PRs, issues, docs, or logs.

## Output States

```text
MERGED:
PR:
MAIN_SHA:
CI:
DEPLOYMENT_MODE:
```

```text
QUARANTINED:
PR:
REASON:
EVIDENCE:
```

```text
BLOCKED:
PR:
BLOCKER:
NEXT_ACTION:
```
