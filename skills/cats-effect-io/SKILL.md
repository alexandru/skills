---
name: cats-effect-io
description: Helps agents write and review Scala Cats Effect IO code. Use for suspending side effects and non-determinism in IO or F[_], choosing Sync/Async/Temporal/Concurrent/Clock/Random, handling blocking I/O, testing with TestControl, and composing resources, fibers, races, and structured concurrency safely.
---

# Cats Effect IO (Scala)

## Quick start

- Treat every side effect and source of non-determinism as an effect value: return `IO[A]`, `SyncIO[A]`, or `F[A]` with the smallest needed Cats Effect capability.
- Suspend each side-effectful call, not a precomputed result. `Instant.now()`, random/UUID generation, environment reads, and mutable allocation such as `new Array[...]` belong inside `IO(...)`, `Sync[F].delay`, `Clock`, `Random`, or an effectful factory.
- Initialize shared mutable state through `IO`/`F`/`Resource` factories and pass the resulting reference or service around. Do not hide effects in constructors, top-level vals, or default arguments.
- Wrap Java blocking use-phase calls with `IO.interruptible` by default (or `Sync[F].interruptible`); use `blocking` for acquisition, finalizers, and operations that must not be interrupted.
- Use `Resource` to acquire/release resources and `IOApp` for program entry points.
- Prefer structured concurrency (`parTraverse`, `parMapN`, `background`, `Supervisor`) over manual fiber management.
- Do not use `unsafeRun*` (`unsafeRunSync`, `unsafeRunAndForget`, etc.) in app code or tests; for interop with non-Cats-Effect callback APIs, use `Dispatcher`.
- Read `references/cats-effect-io.md` for concepts, recipes, FAQ guidance, and verified samples.
- For deeper `Resource` guidance, use the `cats-effect-resource` skill (install: `npx skills add https://github.com/alexandru/skills --skill cats-effect-resource`).

## Workflow

1. Identify every side effect and non-deterministic value, including time, random values, mutable allocation, and shared-state reads/writes.
2. Choose the effect type: concrete `IO` or polymorphic `F[_]` with the smallest capability (`Clock`, `Random`, `Sync`, `Async`, `Temporal`, `Concurrent`, etc.).
3. Wrap side-effectful code using `IO(...)`, `IO.interruptible`, `IO.blocking`, `IO.async`, or the corresponding typeclass operation.
4. Move initialization of stateful services into `create`/`resource` factories returning `F[A]` or `Resource[F, A]`.
5. Compose effects with `flatMap`/for-comprehensions and collection combinators (`traverse`, `parTraverse`).
6. Use concurrency primitives (`Ref`, `Deferred`, `Queue`, `Semaphore`, `Supervisor`) and structured concurrency to avoid fiber leaks.
7. Keep effect execution at boundaries (`IOApp`, framework runtime); for callback-style interop, bridge with `Dispatcher`.

## Side-effect rules (apply to `IO`, `SyncIO`, and to `F[_]: Sync/Async`)

- All side-effectful functions must return results wrapped in `IO` (or `F[_]` with Cats Effect typeclasses/capabilities).
- Side effects include all non-determinism (call sites are not referentially transparent):
  - Any I/O (files, sockets, console, databases).
  - `Instant.now()`, `System.currentTimeMillis()`, `Random.nextInt()`, `UUID.randomUUID()`.
  - Reads from environment variables, system properties, clocks, random sources, or shared mutable state.
  - Allocating or returning mutable structures when identity or mutation can escape (`Array`, `mutable.Map`, Java collections, `AtomicReference`, caches).
- Private local mutation is acceptable only when the whole mutable block is suspended and no mutable value escapes.

## Blocking I/O rules

- Prefer `IO.interruptible`/`Sync[F].interruptible` for blocking use-phase operations. This gives cancellation a chance to interrupt the underlying thread and is the right default for network/socket-style blocking APIs.
- Do not require a proof that every Java API honors interruption before using `interruptible`; some APIs still ignore interruption, so add a resource-specific cancellation protocol when cancellation responsiveness matters and testing shows interruption is not enough.
- Use `IO.blocking`/`Sync[F].blocking` for acquisition, cleanup, and disposal (`Closeable#close`, `AutoCloseable#close`), where attempted interruption can leave lifecycle state ambiguous.

## Output expectations

- Make side effects explicit in signatures (`IO`/`SyncIO` or `F[_]: Sync/Async`); the guidance here applies equally to concrete `IO` and polymorphic `F[_]`.
- Use the smallest typeclass constraint that supports the needed operations.
- Keep effects as values; do not execute effects in constructors or top-level vals.
- When adding or changing Scala examples, update and compile the bundled `scripts/verify-examples.scala` script.

## Execution and test rules

- `unsafeRun*` is forbidden in production and test code, including `import cats.effect.unsafe.implicits.global`.
- If interop requires running effects from non-Cats-Effect callbacks, use `Dispatcher`.
- Prefer effect-native test styles (return `IO[Assertion]`/`F[Assertion]`) instead of manually running effects.
- Avoid `IO.sleep`/`Thread.sleep` in unit tests unless using virtual time with `TestControl`.

## References

- Load `references/cats-effect-io.md` for documentation summary and patterns.
- For concrete samples, read `references/cats-effect-io.md`; the representative check is `scripts/verify-examples.scala`.
- Use the `cats-effect-resource` skill for Resource-specific workflows and patterns (install: `npx skills add https://github.com/alexandru/skills --skill cats-effect-resource`).
