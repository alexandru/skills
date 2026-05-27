# Skills Repository

This is a collection of skills for use with AI Agents. See:

- [Claude Skills](https://code.claude.com/docs/en/skills)
- [Copilot Agent Skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)

## Usage

```
npx skills add https://github.com/alexandru/skills --skill <skill-name>
```

## Skills

- [akka-streams](./skills/akka-streams/): Akka Streams and Pekko Streams reactive streaming patterns and testing
- [arrow-resource](./skills/arrow-resource/): Arrow Resource lifecycle discipline, context-parameter builders, and arrow-autoclose fallback patterns
- [arrow-typed-errors](./skills/arrow-typed-errors/): Context-parameter Raise DSL, efficient Either composition, and validation guidance
- [cats-effect-resource](./skills/cats-effect-resource/): Cats Effect Resource lifecycle management patterns
- [cats-effect-io](./skills/cats-effect-io/): Cats Effect IO usage patterns and typeclass guidance
- [cats-mtl-typed-errors](./skills/cats-mtl-typed-errors/): Scala typed errors using Cats MTL Raise/Handle and allow/rescue
- [compose-state-hoisting](./skills/compose-state-hoisting/): Compose state hoisting and state ownership guidance
- [create-skill](./skills/create-skill/): Guide for creating effective agent skills
- [jspecify-nullness](./skills/jspecify-nullness/): JSpecify nullness annotations for Java APIs and tooling
- [kotlin-context-parameters](./skills/kotlin-context-parameters/): Kotlin context parameter syntax, patterns, and migration guidance
- [kotlin-java-library](./skills/kotlin-java-library/): Kotlin design for Java libraries and Java consumers
- [simplify](./skills/simplify/): Behavior-preserving code simplification and readability-focused refactoring

## Testing

Each skill's references include guidance for representative requests. Executable Kotlin checks for Arrow guidance live in [`samples/arrow-typed-errors-context.kt`](./samples/arrow-typed-errors-context.kt) and [`samples/arrow-resource-context.kt`](./samples/arrow-resource-context.kt).

## License

MIT
