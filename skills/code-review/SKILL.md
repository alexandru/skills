---
name: code-review
description: Reviews code changes for bugs, structural problems, performance issues, and unintended behavior. Use when reviewing uncommitted changes, commits, branches, or pull requests.
---

When doing a code review, follow these rules.

## Determining what to review

Choose the review scope from the user's request:

1. **No target**: Review uncommitted changes with `git diff`, `git diff --cached`, and `git status --short`; read untracked files in full.
2. **Commit**: Run `git show --find-renames <commit>`.
3. **Branch or base ref**: Run `git diff <base-ref>...HEAD`. If the branch is already merged and this is empty, recover the historical base and head from pull-request metadata.
4. **Pull request URL or number**:
   - GitHub: run `gh pr view <pr>` and `gh pr diff <pr>`.
   - Azure DevOps: parse the URL, run `az repos pr show --id <pr-id> --organization <organization-url> --project <project>`, and construct the diff from the recorded commit IDs. For a merged pull request, use its iteration or merge metadata rather than the current target branch.
   - Treat a bare number as a pull request only when the request or repository provider makes this clear.

Confirm that the ref or pull request resolves and the diff is non-empty. If provider authentication or metadata is unavailable, report that instead of choosing another diff.

---

## Identifying the spec source

Look for the intended requirements in this order:

1. A path, URL, issue or work-item ID, or requirements text supplied by the user.
2. A specification or work item linked from the pull request.
3. Issue references in commit messages, using the repository's configured issue-tracker workflow.
4. Ask the user.

If a supplied source cannot be accessed, ask the user for its contents. If the user confirms that no specification exists, continue the review and state that no spec was available.

---

## Gathering Context

**Diffs alone are not enough.** After getting the diff, read the entire file(s) being modified to understand the full context. Code that looks wrong in isolation may be correct given surrounding logic—and vice versa.

- Use the diff to identify which files changed
- For worktree reviews, read each relevant untracked file completely
- Read the full file to understand existing patterns, control flow, and error handling
- Check for existing style guide or conventions files (CONVENTIONS.md, AGENTS.md, .editorconfig, etc.)

---

## What to Look For

**Bugs** - Your primary focus.

- Logic errors, off-by-one mistakes, incorrect conditionals
- If-else guards: missing guards, incorrect branching, unreachable code paths
- Edge cases: null/empty/undefined inputs, error conditions, race conditions
- Security issues: injection, auth bypass, data exposure
- Broken error handling that swallows failures, throws unexpectedly or returns error types that are not caught.

**Structure** - Does the code fit the codebase?

- Does it follow existing patterns and conventions?
- Are there established abstractions it should use but doesn't?
- Excessive nesting that could be flattened with early returns or extraction

**Performance** - Only flag if obviously problematic.

- O(n²) on unbounded data, N+1 queries, blocking I/O on hot paths

**Behavior Changes** - If a behavioral change is introduced, raise it (especially if it's possibly unintentional).

**Spec compliance** - When a spec is available, flag missing or incorrectly implemented requirements. Cite the relevant requirement.

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
- Don't flag style preferences as issues unless they clearly violate established project conventions.

---

## Tools

Use these to inform your review:

- **Codebase context** - Find how existing code handles similar problems. Check patterns, conventions, and prior art before claiming something doesn't fit.
- **Library/API context** - Use relevant available skills or approved documentation to verify library/API usage before flagging it as wrong.
- **Web Search** - Research best practices if you're unsure about a pattern.

If you're uncertain about something and can't verify it with these tools, say "I'm not sure about X" rather than flagging it as a definite issue.

---

## Output

1. If there is a bug, be direct and clear about why it is a bug.
2. Clearly communicate severity of issues. Do not overstate severity.
3. Critiques should clearly and explicitly communicate the scenarios, environments, or inputs that are necessary for the bug to arise. The comment should immediately indicate that the issue's severity depends on these factors.
4. Your tone should be matter-of-fact and not accusatory or overly positive. It should read as a helpful AI assistant suggestion without sounding too much like a human reviewer.
5. Write so the reader can quickly understand the issue without reading too closely.
6. AVOID flattery, do not give any comments that are not helpful to the reader. Avoid phrasing like "Great job ...", "Thanks for ...".
7. Cite the affected file and line for each finding.
