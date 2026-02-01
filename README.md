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
- [compose-state-hoisting](./skills/compose-state-hoisting/): Compose state hoisting and state ownership guidance

## License

MIT
