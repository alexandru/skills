---
name: simplify
description: Runs a behavior-preserving simplification loop using a reviewer subagent and the simplifying criteria. Use when the user invokes /simplify with an optional scope.
disable-model-invocation: true
---

## Criteria

Load the `simplifying` skill and use each lens. If it is not installed, install it with:

```sh
npx skills add https://github.com/alexandru/skills --skill simplifying
```

Simplification is refactoring. Behavior MUST NOT change unless the user explicitly requests that change.

## Scope and context

Use the scope supplied after `/simplify`. Without one, use the current staged and unstaged diff, including untracked source files. If there is no code to review, report that and stop.

The scope identifies where to start looking, not a hard editing boundary. Necessary changes to callers, consumers, or neighboring modules are allowed; unrelated cleanup is not.

Gather the context the reviewer needs: the request and scope, exact file paths and relevant diffs, specifications and requirements, applicable project instructions and conventions, public contracts, known hot paths, and verification procedures. Pass the relevant text or accessible paths explicitly; the subagent does not inherit the parent conversation. State any unavailable context rather than inventing it.

## Iteration

1. **Review.** Launch one reviewer subagent. Supply the context above, the current code, previous findings with their disposition, and [the reviewer instructions](references/reviewer.md). Tell it to load and follow `simplifying`, then report findings without editing code.
2. **Refactor.** Evaluate the findings and implement worthwhile changes without asking for approval. Where existing tests do not cover behavior at risk, add characterization tests before changing the code. Keep applied and rejected findings in the conversation; do not reconsider a rejected proposal unless new evidence changes its basis.
3. **Verify.** Run the project's relevant tests and checks after the changes, and fix failures before another review. Do not alter expected behavior to make verification pass. If verification cannot be completed or progress is blocked, stop and report the limitation.
4. **Repeat.** Update the review context with the changed code, verification results, and findings already applied or rejected. Continue until no actionable findings remain. No arbitrary round limit is required.

## Final response

Give the user a concise summary of the changes, verification results, and any unresolved findings or behavior-changing proposals.
