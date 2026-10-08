---
name: simplify
description: Simplifies code without changing behavior, using the lenses of the simplicity skill. Use when the user invokes /simplify with an optional scope.
disable-model-invocation: true
---

Load the `simplicity` skill and simplify the code in scope with its lenses: constraints, simplicity, and parametricity. If it is not installed, install it with:

```sh
npx skills add https://github.com/alexandru/skills --skill simplicity
```

Use the scope supplied after `/simplify`; without one, use the current staged and unstaged diff, including untracked source files. If there is no code to simplify, say so and stop. The scope is where to start, not an editing boundary: necessary changes to callers and consumers are allowed, unrelated cleanup is not.

Simplification is refactoring: behavior MUST NOT change unless the user explicitly requests that change.

Every simplification you apply MUST be explained by a lens from `simplicity`: name the lens and state, in that lens's terms, what complexity the change removes. A change without that explanation is not a simplification and MUST NOT be applied, whatever it does to the line count.

Lines of code do not measure simplicity. Fewer lines often accompany a genuine simplification, but the correlation is not the justification: line counts MUST NOT justify a change, and a lens-justified change MAY add lines.

Run the project's tests and checks for the code you changed, and fix failures without altering expected behavior. Report the changes, the lens justifying each one, the verification results, and anything you found but did not change.
