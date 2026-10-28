---
name: cats-effect-resource
description: Helps agents write and review Scala Cats Effect Resource code. Use for preventing resource leaks and use-after-release bugs, modeling disposable values with Resource, designing Resource-returning factories and constructor-injected services, wrapping Java AutoCloseable values, composing resources, and handling cancellation-safe release.
---

# Cats Effect Resource (Scala)

## Quick start
- Model every owned disposable value with `Resource.make`, `Resource.makeCase`, or `Resource.fromAutoCloseable`.
- Never return an acquired handle from `.use`; it is released when `.use` completes. Return only values computed inside the scope.
- Classes must not allocate owned resources in constructors, fields, or top-level vals. Use companion/factory methods returning `Resource[F, Service]`, then pass acquired private dependencies into constructors.
- Wrap Java `AutoCloseable` values with `Resource.fromAutoCloseable(Sync[F].blocking(...))` or `IO.blocking(...)`.
- Compose resources with `flatMap`, `mapN`, `parMapN`, or helper constructors; expose `Resource[F, A]` from lifecycle-owning APIs.
- Read `references/resource.md` for patterns, best practices, and type-checked samples.

## Workflow
1. Identify every value that needs disposal or lifecycle shutdown.
2. Move acquisition and release into a `Resource[F, A]`; suspend side effects in `F` (`Sync[F].delay`/`blocking`, `IO.blocking`, etc.).
3. Build classes from already-acquired constructor parameters; put construction in `resource`/`create` factories that return `Resource`.
4. Compose lower-level resources into higher-level resources before `.use`.
5. Run with `.use` at the lifecycle boundary (IOApp, server startup, test fixture), and keep raw handles inside the use scope.
6. Use `allocated` only for interop that truly needs separate acquire/release, and guarantee the finalizer is called exactly once.

## Usage guidance
- Prefer `Resource` over `try/finally` or `bracket` when composition and cancelation safety matter.
- Use `IO.blocking` (or `Sync[F].blocking`) for acquisition and release when calling blocking JVM APIs.
- Prefer `IO.interruptible`/`Sync[F].interruptible` for blocking use-phase operations inside `.use`.
- Use `Resource.eval` only for effects that do not own a finalizer; it is not a substitute for resource acquisition.
- `use` acquires a fresh resource each time. If the same handle must be shared for multiple operations, do those operations inside one `.use`.
- For background fibers, use `Resource`, `.background`, or `Supervisor` to ensure cleanup on cancelation.
- When adding or changing Scala examples, update and compile the bundled `scripts/verify-examples.scala` script.

## References
- Load `references/resource.md` for API details, patterns, and examples; the representative check is `scripts/verify-examples.scala`.
- For Kotlin/Arrow parallels, see the `arrow-resource` skill.
- Install this skill with `npx skills add https://github.com/alexandru/skills --skill cats-effect-resource`.
