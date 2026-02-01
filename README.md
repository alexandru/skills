# Skills Repository

This is a collection of skills for use with AI Agents. See:

- [Claud Skills](https://code.claude.com/docs/en/skills)
- [Copilot Agent Skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)

## Structure

```
skills/
|-- arrow-resource/
|   |-- SKILL.md
|   `-- references/
|       `-- resource.md
|-- arrow-typed-errors/
|   |-- SKILL.md
|   `-- references/
|       `-- typed-errors.md
|-- cats-effect-io/
|   |-- SKILL.md
|   `-- references/
|       `-- cats-effect-io.md
|-- cats-mtl-typed-errors/
|   |-- SKILL.md
|   `-- references/
|       `-- custom-error-types.md
`-- compose-state-hoisting/
    |-- SKILL.md
    `-- references/
        `-- compose-state-guidance.md
```

## Usage

```
npx skills add https://github.com/alexandru/skills --skill <skill-name>
```

## Skills

- [arrow-resource](./skills/arrow-resource/): Resource lifecycle management patterns with Arrow
- [arrow-typed-errors](./skills/arrow-typed-errors/): Typed error modeling and Raise DSL guidance
- [cats-effect-io](./skills/cats-effect-io/): Cats Effect IO usage patterns and typeclass guidance
- [cats-mtl-typed-errors](./skills/cats-mtl-typed-errors/): Scala typed errors using Cats MTL Raise/Handle and allow/rescue
- [compose-state-hoisting](./skills/compose-state-hoisting/): Compose state hoisting and state ownership guidance

## License

MIT
