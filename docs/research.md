# Research Summary

> **Research status:** Point-in-time analysis captured on 2026-06-20. Links and the GitHub feature boundary below were rechecked on 2026-08-19. Product availability, provider behavior, pricing, and operational semantics may change; verify them before implementation.

The reference thread describes a post-PR integration problem. Multiple agents finish work, then each tries to merge or deploy. Since each merge advances `main`, the other attempts become stale and repeat CI, rebase, lock, and retry work.

The important distinction: worktrees and branch discipline prevent local filesystem collisions, but they do not by themselves solve protected-branch queueing, merge-group validation, required checks, or deployment locks.

## Applicability Boundary

The problem appears only after parallel workstreams become independent PR producers. It should not be generalized to all agent delegation.

| Topology | Integration owner | Relevant here? |
| --- | --- | --- |
| Read-only subagents | Parent task | No |
| Shared-working-tree editing subagents | Parent task with disjoint file ownership | Usually no |
| Isolated local worktrees | Parent task or PR workflow, depending on review needs | Sometimes |
| Independent cloud/local agents opening PRs | Protected queue or coordinator | Yes |
| Multi-team, high-volume PR stream | Merge queue or integration service | Yes |

The decision point is not the number of agents. It is whether they hand off independently reviewable PRs that contend for a protected integration path.

## Existing Solution Classes

| Solution class | Fit | Main caveat |
| --- | --- | --- |
| GitHub merge queue | First-party protected merge queue that validates queued changes against the current base plus earlier queued changes. | CI must run on `merge_group`. Current GitHub documentation limits availability to public organization-owned repositories and private organization repositories on Enterprise Cloud. |
| Graphite merge queue | Strong fit for teams already using Graphite stacks or willing to adopt its queue and parallel CI model. | Third-party operational dependency and queue semantics. |
| Mergify batch queue | Strong fit when the desired behavior is one CI/deploy wave for several PRs. | Requires configuring batch policy and accepting its merge semantics. |
| AGENTS-only coordination | Useful guardrail: workers do not merge, one coordinator owns `main`. | Not enough for throughput unless backed by a real queue, batch validation, or coordinator implementation. |

## Research Conclusion

The solution is not "make every agent better at retrying." The solution is one protected write path to `main`, with integration validation before the base branch moves.

The smallest practical adoption path is:

1. enable a real merge queue where available;
2. make CI run against the merge group or integration branch;
3. separate production deploy concurrency from PR validation;
4. give agents explicit instructions to stop after requesting merge;
5. batch compatible PRs and split failed batches.

For lower-scale Codex work, the smaller adoption path is often to keep one parent responsible for integration and verification, without introducing a PR queue at all.

## Evidence And Claim Limits

- The benchmark is a deterministic model under stated CI, merge-overhead, batch-size, and concurrency assumptions.
- The real-repository exercise used synthetic branches in an isolated clone; it was not a production deployment or a sustained merge-queue trial.
- The results show that batching can reduce modeled duplicate CI work and can isolate an injected bad branch under the tested algorithm. They do not prove universal speed, reliability, or production safety.
- GitHub's documentation currently distinguishes merge limits from merge-group build combination. Provider-specific batching must therefore be verified rather than inferred from the word "batch."
- Third-party provider features, pricing, and queue semantics were not comprehensively re-evaluated on 2026-08-19.

## Public References

- GitHub merge queue docs: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue
- GitHub `merge_group` event docs: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#merge_group
- Graphite merge queue docs: https://graphite.com/docs/graphite-merge-queue
- Mergify batch queue docs: https://docs.mergify.com/merge-queue/batches/
