# Research Summary

The reference thread describes a post-PR integration problem. Multiple agents finish work, then each tries to merge or deploy. Since each merge advances `main`, the other attempts become stale and repeat CI, rebase, lock, and retry work.

The important distinction: worktrees and branch discipline prevent local filesystem collisions, but they do not by themselves solve protected-branch queueing, merge-group validation, required checks, or deployment locks.

## Existing Solution Classes

| Solution class | Fit | Main caveat |
| --- | --- | --- |
| GitHub merge queue | First-party protected merge queue that validates queued changes against the current base plus earlier queued changes. | CI must run on `merge_group`; availability depends on repository and plan shape. |
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

## Public References

- GitHub merge queue docs: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue
- GitHub `merge_group` event docs: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#merge_group
- Graphite merge queue docs: https://graphite.com/docs/graphite-merge-queue
- Mergify batch queue docs: https://docs.mergify.com/merge-queue/batches/
