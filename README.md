# Skills Repository

A collection of reusable code skills meant to be indexed by [skills.sh](https://skills.sh).

## About

This repository contains curated code snippets, utilities, and functions that can be discovered and used across projects.

## Structure

```
skills/
|-- arrow-resource/
|   |-- SKILL.md
|   `-- references/
|       `-- resource.md
`-- arrow-typed-errors/
    |-- SKILL.md
    `-- references/
        `-- typed-errors.md
```

## Usage

Each skill is contained in its own directory with:
- `skill.json`: Metadata describing the skill (name, description, tags, etc.)
- `README.md`: Detailed documentation
- Implementation file(s): The actual code

## Skills

- [arrow-resource](./skills/arrow-resource/): Resource lifecycle management patterns with Arrow
- [arrow-typed-errors](./skills/arrow-typed-errors/): Typed error modeling and Raise DSL guidance

## Contributing

To add a new skill:
1. Create a new directory under `skills/`
2. Add a `skill.json` with metadata
3. Add a `README.md` with documentation
4. Add your implementation files

## License

MIT
