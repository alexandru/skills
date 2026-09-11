---
name: code-review
description: Reviews code changes for bugs, structural problems, performance issues, and unintended behavior. Use when reviewing uncommitted changes, commits, branches, or pull requests.
---

When doing a code review, follow these rules.

## Determining what to review

Choose the review scope from the user's request:

1. **No target**: The staged and unstaged diffs, plus untracked files and their contents.
2. **Commit**: The commit metadata and patch.
3. **Branch or base ref**: The merge-base, commits since that base, and the branch diff. If the branch is already merged, its historical base and head from pull-request metadata.
4. **Pull request URL or number**: The pull-request context, base and head commits, commit list, and historical diff. For a merged pull request, include its historical iteration or merge metadata. Treat a bare number as a pull request only when the request or repository provider makes this clear.

If the requested target or provider metadata is unavailable, report that instead of choosing a different review scope.

---

## Identifying the spec source

Look for the intended requirements in this order:

1. A path, URL, issue or work-item ID, or requirements text supplied by the user.
2. A specification or work item linked from the pull request.
3. Issue references in commit messages, using the repository's configured issue-tracker workflow.

If a source cannot be accessed or no specification is found, continue without asking for one and state the limitation. Requirements inform the bugs task when available; they are not a prerequisite for either task.

---

## Identifying the standards sources

Anything in the repo that documents how code should be written, such as `CODING_STANDARDS.md` or `CONTRIBUTING.md`.

Include applicable `AGENTS.md` files and the conventions files found while gathering context. Read [the smell baseline](references/coding-standards.md) and include it in the coding standards task even when the repository documents no standards.

---

## Starting the parallel reviews

Run two review subtasks in parallel: **Bugs** and **Coding standards**. The bugs task reviews behavior; the coding standards task reviews non-bug structure and conventions. The parent gathers the shared inputs, starts both tasks, and assembles their reports.

Give both subtasks:

- The review target, diff command or captured diff, relevant commit metadata and commit list, and any untracked files in scope.
- The repository location, discovered context paths, and any unavailable inputs.
- The shared context, finding, tool, and output rules below, pasted in full. Each task must be able to read the relevant files and gather additional evidence.

Give the **Bugs** task the bugs brief below and any requirements paths or fetched contents. Give the **Coding standards** task the coding standards brief below, the standards-source paths, and the complete smell baseline pasted in full. Do not assume either task inherits the parent's instructions.

Start both tasks before waiting for either result. Each task performs its own review and assigns severity. Do not turn them into a spec task and a standards task.

---

## Gathering Context

**Diffs alone are not enough.** After getting the diff, read the entire file(s) being modified to understand the full context. Code that looks wrong in isolation may be correct given surrounding logic—and vice versa.

- Use the diff to identify which files changed
- For worktree reviews, read each relevant untracked file completely
- Read the full file to understand existing patterns, control flow, and error handling
- Check for existing style guide or conventions files (CONVENTIONS.md, AGENTS.md, .editorconfig, etc.)

---

## Bugs task

**Bugs** - Your primary focus.

- Logic errors, off-by-one mistakes, incorrect conditionals
- If-else guards: missing guards, incorrect branching, unreachable code paths
- Edge cases: null/empty/undefined inputs, error conditions, race conditions
- Security issues: injection, auth bypass, data exposure
- Broken error handling that swallows failures, throws unexpectedly or returns error types that are not caught.

**Performance** - Only flag if obviously problematic.

- O(n²) on unbounded data, N+1 queries, blocking I/O on hot paths

**Behavior Changes** - If a behavioral change is introduced, raise it (especially if it's possibly unintentional).

**Spec compliance** - When a spec is available, flag missing or incorrectly implemented requirements. Cite the relevant requirement.

Leave non-bug structure and convention findings to the coding standards task.

---

## Coding standards task

Review the diff against the discovered repository standards and the supplied smell baseline. Report documented-standard violations with the standard's file and rule. For baseline smells, name the smell and quote the relevant hunk. Apply the baseline's rules for judgment calls, repository overrides, and tooling-enforced issues.

**Structure** - Does the code fit the codebase?

- Does it follow existing patterns and conventions?
- Are there established abstractions it should use but doesn't?
- Excessive nesting that could be flattened with early returns or extraction

Report non-bug issues here, not behavioral failures. Explain the violation or structural concern and its impact.

---

## Before You Flag Something

**Be certain.** If you're going to call something a bug, you need to be confident it actually is one.

- Only review the changes - do not review pre-existing code that wasn't modified
- Don't flag something as a bug if you're unsure - investigate first
- Don't invent hypothetical problems - if an edge case matters, explain the realistic scenario where it breaks
- If you need more context to be sure, use the tools below to get it

**Don't be a zealot about style.** When checking code against conventions:

- Verify the code is _actually_ in violation. Don't complain about else statements if early returns are already being used correctly.
- Some "violations" are acceptable when they're the simplest option. A `let` statement is fine if the alternative is convoluted.
- Excessive nesting is a legitimate concern regardless of other style choices.
- Don't flag personal style preferences. Report established-project-convention violations or baseline smell judgments.

---

## Tools

Use these to inform your review:

- **Codebase context** - Find how existing code handles similar problems. Check patterns, conventions, and prior art before claiming something doesn't fit.
- **Library/API context** - Use relevant available skills or approved documentation to verify library/API usage before flagging it as wrong.
- **Web Search** - Research best practices if you're unsure about a pattern.

If you're uncertain about something and can't verify it with these tools, say "I'm not sure about X" rather than flagging it as a definite issue.

---

## Output

Each subtask uses `Critical`, `High`, `Medium`, or `Low` severity, based on its judgment and applicable repository documentation. Assess severity, not whether the PR should merge or a finding should block it.

1. If there is a bug, be direct and clear about why it is a bug.
2. Clearly communicate severity of issues. Do not overstate severity.
3. Critiques should clearly and explicitly communicate the scenarios, environments, or inputs that are necessary for the bug to arise. The comment should immediately indicate that the issue's severity depends on these factors.
4. Your tone should be matter-of-fact and not accusatory or overly positive. It should read as a helpful AI assistant suggestion without sounding too much like a human reviewer.
5. Write so the reader can quickly understand the issue without reading too closely.
6. AVOID flattery, do not give any comments that are not helpful to the reader. Avoid phrasing like "Great job ...", "Thanks for ...".
7. Cite the affected file and line for each finding.

Use a numbered level-three heading for each finding, containing its severity in square brackets and a short, specific title. Follow it with a **Location:** field containing the file and line range, then explain the finding and its impact. Coding standards findings also include a **Standard:** field citing the rule's file and lines when available. For unwritten conventions or structural concerns, identify the established pattern or explain the concern instead of inventing a standards citation.

The parent presents the reports under `## Bugs` and then `## Coding standards`, verbatim or lightly cleaned for formatting. Keep both sections even when empty, stating that no issues were found. Do not perform another review or verification pass, deduplicate findings, or merge or rerank the two axes.
