# AGENTS: Adding a Reusable Skill

Reference: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices

## Core principles (keep SKILL.md lean)
- Be concise: SKILL.md is loaded into context; every token competes with the user’s request.
- Assume the agent is smart: only add context it wouldn’t already know.
- Use progressive disclosure: keep detailed explanations and examples in `references/*.md`.

## Naming + metadata
- `name` must be lowercase, numbers, hyphens only; prefer a clear action or domain name.
- `description` must be third-person, specific, and include “when to use”.

## Structure
- `skills/<skill-name>/SKILL.md` contains quick start, workflow, rules, and pointers to references.
- `skills/<skill-name>/references/*.md` holds extended explanations and examples.
- Keep references one level deep from SKILL.md (no nested references).
- Add a table of contents for reference files longer than ~100 lines.
- Cross-skill references are allowed, but must include install instructions (e.g., `npx skills add https://github.com/alexandru/skills --skill <skill-name>`).

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
5. Test with representative prompts and refine.

## Checklist
- [ ] Name/description meet format rules and are specific.
- [ ] SKILL.md is concise and directs to references.
- [ ] Examples are in references, not SKILL.md.
- [ ] No nested references; one level deep from SKILL.md.
- [ ] `skills.json` version updated per semantic versioning rules.
- [ ] `skills.json` updated with tags.
- [ ] `README.md` updated.
- [ ] Tested with at least a few real requests.
