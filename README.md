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
- [arrow-resource](./skills/arrow-resource/): Resource lifecycle management patterns with Arrow
- [arrow-typed-errors](./skills/arrow-typed-errors/): Typed error modeling and Raise DSL guidance
- [cats-effect-resource](./skills/cats-effect-resource/): Cats Effect Resource lifecycle management patterns
- [cats-effect-io](./skills/cats-effect-io/): Cats Effect IO usage patterns and typeclass guidance
- [cats-mtl-typed-errors](./skills/cats-mtl-typed-errors/): Scala typed errors using Cats MTL Raise/Handle and allow/rescue
- [compose-state-hoisting](./skills/compose-state-hoisting/): Compose state hoisting and state ownership guidance
- [jspecify-nullness](./skills/jspecify-nullness/): JSpecify nullness annotations for Java APIs and tooling
- [kotlin-java-library](./skills/kotlin-java-library/): Kotlin design for Java libraries and Java consumers

## Testing

Each skill's references include brief "Test prompts" to validate the guidance against representative requests.

## License

MIT
