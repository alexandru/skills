# AGENTS: Adding a Reusable Skill

Reference: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices

## Core principles (keep SKILL.md lean)
- Be concise: SKILL.md is loaded into context; every token competes with the user’s request.
- Assume the agent is smart: only add context it wouldn’t already know.
- Use progressive disclosure: keep detailed explanations and examples in `references/*.md`.
- Keep the SKILL.md body under ~500 lines; split details before it becomes a reference manual.
- Keep each instruction in one place: do not repeat detailed guidance in SKILL.md and its references.

## Instruction design
- Match specificity to risk: use guidance for judgment calls, parameterized patterns when a preferred route exists, and exact commands/scripts for fragile or consistency-critical work.
- Give a sensible default instead of listing interchangeable alternatives; mention an alternative only when its trigger is materially different.
- For multi-step or quality-critical tasks, define a validation loop: produce or edit, validate, fix failures, and validate again before finishing.
- Prefer bundled scripts for deterministic repeated operations. State whether an agent should run a script or read it as reference, and make script failures actionable.

## Naming + metadata
- `name` must be at most 64 characters, contain lowercase letters, numbers, and hyphens only, and contain no XML tags or reserved words such as `anthropic` or `claude`; prefer a clear action or domain name.
- `description` must be non-empty, at most 1024 characters, contain no XML tags, be written in third person, be specific, and include what the skill does and “when to use” it.
- Include trigger terms in `description`; agents choose whether to load the skill from this field before reading SKILL.md.

## Structure
- `skills/<skill-name>/SKILL.md` contains quick start, workflow, rules, and pointers to references.
- `skills/<skill-name>/references/*.md` holds extended explanations and examples.
- `skills/<skill-name>/scripts/*` holds reusable deterministic operations or validators when prose alone is insufficient.
- Skill-local verification scripts must live under `skills/<skill-name>/scripts/`, because root-level harness files are not distributed with an installed skill.
- Keep references one level deep from SKILL.md (no nested references).
- Add a table of contents for reference files longer than ~100 lines.
- Cross-skill references are allowed, but must include install instructions (e.g., `npx skills add https://github.com/alexandru/skills --skill <skill-name>`).
- Use descriptive filenames and forward-slash paths in skill instructions.

## Guidance quality
- Prefer the smallest needed typeclass/constraint or API surface.
- Avoid time-sensitive guidance; move outdated info to an “old patterns” section if needed.
- Use consistent terminology across the skill.
- Provide concrete examples only when they materially improve correctness.
- Provide original sources (web links) in references; keep sources high-quality.

## Versioning (skills.json)
- Version uses semantic versioning (e.g., `1.0.0`).
- Increment patch for minor fixes (typos, code sample mistakes).
- Increment minor when adding a new skill.
- Increment major for more substantial skill changes.

## Workflow for adding a skill
1. Create `skills/<skill-name>/SKILL.md` with YAML frontmatter and concise instructions.
2. Add reference docs under `skills/<skill-name>/references/` as needed.
3. Register the skill in `skills.json` (name, path, description, tags).
4. Update `README.md` so the skill list and structure stay current.
5. Validate examples and any scripts, then test with representative prompts and refine.

## Verification
- Type-check API examples rather than publishing plausible snippets. Keep an executable representative sample when a skill teaches non-trivial library APIs.
- For Kotlin skills, take the JBang directives and dependency-pinning approach in `./templates/kotlin-script.kt` as the starting harness; adapt it into a skill-local script that compiles and runs the documented APIs.
- For Scala skills, take the Scala CLI shebang/directive and dependency-pinning approach in `./templates/scala-script.scala` as the starting harness; adapt it into a skill-local script that compiles and runs the documented APIs.
- Use the same language/compiler and library features the reference recommends. If a feature requires an opt-in or compiler flag, show and test that flag in the sample.
- Run the validator or executable sample, fix failures, and rerun until it passes; record any intentionally untested snippets.
- Exercise the skill with representative requests, including error-prone or boundary cases. Where the skill will be used across multiple models, test it with the intended models rather than assuming one model’s behavior generalizes.

## Checklist
- [ ] Name/description meet format rules and are specific.
- [ ] SKILL.md is concise and directs to references.
- [ ] Examples are in references, not SKILL.md.
- [ ] No nested references; one level deep from SKILL.md.
- [ ] API examples and validation scripts have been run or any exception is documented.
- [ ] Kotlin/Scala API guidance has an executable type-checking sample based on the repository harnesses when applicable.
- [ ] `skills.json` version updated per semantic versioning rules.
- [ ] `skills.json` updated with tags.
- [ ] `README.md` updated.
- [ ] Tested with at least a few real requests.
