# Skills Repository

This is a collection of skills for use with AI Agents. See:

- [Claude Skills](https://code.claude.com/docs/en/skills)
- [Copilot Agent Skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)

Part of [alexandru/agents-config](https://github.com/alexandru/agents-config).

## Usage

Every skill is a plain [SKILL.md](https://agentskills.io) folder under a category directory: `engineering/`, `coding/`, or `tools/`.

**Claude Code** — install the collection as a plugin (Claude Code ≥ 2.1.292):

```
claude plugin install alexandru-skills --marketplace alexandru/skills
```

Skills then run as `/alexandru-skills:<skill-name>`; refresh with `claude plugin marketplace update alexandru-skills`.

**GitHub Copilot** — install by skill path (GitHub CLI ≥ 2.90):

```
gh skill install alexandru/skills coding/arrow-resource/SKILL.md
```

**OpenAI Codex** — skills load from `~/.agents/skills/<skill-name>/` or a project's `.agents/skills/<skill-name>/`:

```
git clone https://github.com/alexandru/skills
mkdir -p ~/.agents/skills && cp -R skills/coding/arrow-resource ~/.agents/skills/
```

In a session, `$skill-installer` installs skills from a GitHub repo path.

**Any other agent** — with the [skills CLI](https://skills.sh):

```
npx skills add https://github.com/alexandru/skills --skill arrow-resource
```

or copy a skill folder into your agent's skills directory.

## Skills

<details open>
<summary><strong>Engineering</strong> · 4 skills — practice and workflow</summary>

- [code-refine](./engineering/code-refine/): User-invoked refinement of a scope in rounds until they converge, using `code-refinements` ([source](https://github.com/alexandru/skills/blob/main/engineering/code-refine/SKILL.md))
- [code-refinements](./engineering/code-refinements/): What refined code looks like: the three lenses plus rules for type proofs, no partial calls, explicit signatures, unrepresentable wrong states, and hot paths ([source](https://github.com/alexandru/skills/blob/main/engineering/code-refinements/SKILL.md))
- [code-review](./engineering/code-review/): User-invoked adapter for `code-reviewing`
- [code-reviewing](./engineering/code-reviewing/): Review changed code for bugs, structural problems, performance issues, and unintended behavior

</details>

<details>
<summary><strong>Coding</strong> · 11 skills — language and library guidance</summary>

- [akka-streams](./coding/akka-streams/): Akka Streams and Pekko Streams reactive streaming patterns and testing
- [arrow-resource](./coding/arrow-resource/): Arrow Resource lifecycle discipline, context-parameter builders, and arrow-autoclose fallback patterns
- [arrow-typed-errors](./coding/arrow-typed-errors/): Context-parameter Raise DSL, efficient Either composition, and validation guidance
- [cats-effect-resource](./coding/cats-effect-resource/): Cats Effect Resource leak prevention, factory, lifecycle, and Java interop guidance
- [cats-effect-io](./coding/cats-effect-io/): Cats Effect IO side-effect suspension, typeclass, testing, fiber, and race guidance
- [cats-mtl-typed-errors](./coding/cats-mtl-typed-errors/): Scala typed errors using Cats MTL Raise/Handle and allow/rescue
- [compose-state-hoisting](./coding/compose-state-hoisting/): Compose state hoisting and state ownership guidance
- [jspecify-nullness](./coding/jspecify-nullness/): JSpecify nullness annotations for Java APIs and tooling
- [kotlin-context-parameters](./coding/kotlin-context-parameters/): Kotlin context parameter syntax, patterns, and migration guidance
- [kotlin-java-library](./coding/kotlin-java-library/): Kotlin library API design for Java consumers, JVM annotations, records, and compatibility
- [scala-kindlings-derivation](./coding/scala-kindlings-derivation/): Scala Kindlings auto-derivation for Circe and PureConfig instances

</details>

<details>
<summary><strong>Tools</strong> · 3 skills — agent tooling</summary>

- [create-skill](./tools/create-skill/): Guide for creating effective agent skills
- [external-research](./tools/external-research/): External documentation, public repository, and dependency-artifact research with a persistent cache of Git clones and Maven artifacts
- [mcp-access](./tools/mcp-access/): Call MCP servers when native MCP tools are unavailable or restricted: inspector CLI fallback, then raw JSON-RPC over stdio or HTTP

</details>

## Testing

Each skill's references include guidance for representative requests. Skill-specific examples are type-checked by bundled `scripts/verify-examples.*` files inside each skill directory. Root [`templates/`](./templates/) files include Kotlin, Scala, and Java harness templates only and are not referenced by installed skills.

## License

MIT
