---
name: refine
description: Refines a scope of code in rounds of lens review, triage against the refinements rules, and verified edits, until a round removes no complexity. Every feature stays, no hot path gets slower, and bugs found along the way get fixed. Use when the user asks to refine a scope of code, such as a module, a directory, or the changes on a branch.
disable-model-invocation: true
argument-hint: <scope, e.g. "the planner module" or "the changes on this branch">
---

# Refine

The scope is whatever the user asks to refine; without one, use the current staged and unstaged diff, including untracked source files. If there is no code to refine, say so and stop. A scope that names changes — pending changes, a branch, a pull request — is refined as the diff it names; everything else is an area.

Load the `refinements` skill and hold every change to its rules and its three lenses: constraints, simplicity, and parametricity. If it is not installed, install it with:

```sh
npx skills add https://github.com/alexandru/skills --skill refinements
```

Success is complexity that disappears while every feature stays, every bug found gets fixed, and no hot path gets slower. A round that removes nothing ends the run; there is no line-count quota, and fewer lines is not itself the goal.

You own the plan. The recipe below is the minimum that works, not a schedule — adapt it to the scope.

1. **Ground truth.** Learn how the project verifies: the commands, their normal duration, and what CI runs. Find the scope's hot paths — code that runs per request, per entity, per item or per field — and whether the public API is free to change, which holds only when the project's instructions say so or the code is unreleased. Read the project's agent instructions and conventions, and the spec text when the scope implements one: code deviating from the spec is a bug unless the project documents the deviation, and where the spec leaves an input undefined, code handling it two ways is a bug, settled by the output clients see.
2. **Round.** Review the scope through the three lenses with fresh eyes. Then triage against the code: trace callers before trusting a claim about behavior. Accept a finding only when you can show end-user behavior holds and name the complexity it removes; reject what adds a check per case, handles one more edge case, or grows the code without a removal to pay for it. A real bug is a finding like any other: write a test that fails on it and fix it in the round that finds it, the structural fix where one exists, never later. Don't propose a rejected idea again. Apply one change at a time, running the tests that cover the code it touched after each; revert what goes red and you can't fix.
3. **Repeat** the rounds until one removes nothing. When the rounds stall at local cleanups, look for the redesign: a different core model in which the invalid states can't be written, two passes merged into one, a module that turns out to be unnecessary.
4. **Regressions.** Review the whole run's diff with fresh eyes for regressions: code that worked before a change and is wrong after it, including bugs from two rounds interacting. Give each confirmed one its smallest fix — restore the behavior, not the old code; a fix that only adds a check or a special case is the last resort.
5. **Verify.** Run the project's full verification on the converged state, in every configuration CI builds: the unit suite, plus every conformance, audit or docs build. Fix or revert what fails, then rerun.
6. **Report.** What each removal removed, the bugs fixed with their tests, the verification results, the rejections the user should know about, and anything left for the user to decide: stricter input rules, API breaks, bugs outside the scope.

## Invariants

- Refinement is refactoring: end-user behavior MUST NOT change unless the user explicitly requests it. Internal structure, data types, call order and intermediate representations are free to change; the test suite defines the behavior, and where it misses something a user would notice, pin that with a characterization test before changing the code around it.
- Input the code accepted before stays accepted: a value that parsed, a request that succeeded, data already stored. A stricter input rule breaks the users who sent or stored that input, however clean it is; leave it out and list it in the report as a proposal.
- The public API is behavior — the signatures users compile against, and their doc comments, which state the contract — unless the project's instructions free it, which holds only when they say so or the code is unreleased. A change updates a doc sentence it makes false.
- Tests keep running everywhere they ran before: never narrowed to the configuration CI happens to run, never deleted while their case is uncovered.
- For a diff scope, refine only what the diff added or changed; reach the surrounding code only when the diff's changes force it.
- Give every long command a timeout of about twice its normal duration, and never wait on a hung process.
