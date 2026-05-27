---
name: cats-mtl-typed-errors
description: Helps agents model Scala domain failures with Cats MTL Raise/Handle, allow/rescue, Cats Effect IO, and pure Either tests. Use for designing typed error ADTs, replacing EitherT in effectful flows, choosing IO-only or F[_] APIs, and preserving Typelevel resource/concurrency semantics.
---

# Cats MTL Typed Errors (Scala)

## Quick start
- Model expected domain failures as focused ADTs that do not extend `Throwable` unless interop requires it.
- Use `Raise[F, E]` for functions that can raise `E`; use `Handle[F, E]` only when the function also recovers from `E`.
- Introduce a lexical typed-error scope with `Handle.allow`/`rescue` in Scala 3 or `Handle.allowF`/`rescue` in Scala 2.
- Prefer Cats MTL over pervasive `IO[Either[E, A]]` or `EitherT[IO, E, A]` in effectful Cats Effect code; keep pure `Either[E, A]` for deterministic validation and tests.
- Choose concrete `IO` or polymorphic `F[_]` based on the project style. When using `F[_]`, require the smallest Cats/Cats Effect capability that the function needs.
- For side-effect, blocking, resource, and fiber rules, use the related `cats-effect-io` skill (install: `npx skills add https://github.com/alexandru/skills --skill cats-effect-io`).

## Workflow
1. Model errors as sealed ADTs (Scala 2) or enums (Scala 3), using wrapper cases to compose lower-level errors into higher-level domains.
2. Add `Raise[F, E]` to functions that can fail with `E`; add `Applicative`, `Monad`, or Cats Effect capabilities only as needed.
3. Raise failures with `.raise` or `Raise[F, E].raise`; return successes with `pure`, `map`, and `flatMap`.
4. At an application, route, stream, or service boundary, open an `allow`/`allowF` scope and close it with `rescue`.
5. Keep the `rescue` handler exhaustive for the error ADT and translate to the boundary result, such as `IO[Response]`, fallback `IO[A]`, or pure `Either`.
6. Compile the representative examples after changing guidance: run `scripts/verify-examples.scala` and `scripts/verify-examples-scala2.scala`.

## Patterns to apply
- **Typed signatures**: `Raise[F, E]` is the checked-error capability; it says this function may raise domain error `E`.
- **Boundary handling**: `allow`/`rescue` is analogous to `try`/`catch`, but it works with effect values and ordinary ADTs.
- **Local recovery**: use `Handle[F, E]` plus `handle`/`handleWith` only where recovery is part of that function's contract.
- **Small constraints**: use `Applicative` for `pure` plus `raise`, `Monad` for dependent sequencing, and Cats Effect typeclasses for real effects.
- **Scala 3 first**: prefer `using` and `Handle.allow`; for Scala 2, use `allowF` and explicit implicit parameters.
- **Pure interop**: instantiate `F` as `Either[E, *]`/a type alias in pure tests; lift or translate the result at effect boundaries.
- **Transformer avoidance**: avoid `EitherT` for typed domain errors in Cats Effect flows unless a local transformer scope is clearly simpler.
- **Error composition**: do not make sealed error ADTs inherit from other sealed error ADTs; wrap lower-level errors in outer-domain cases.
- **Throwable handling**: avoid broad `Throwable` recovery inside an `allow` scope unless you intentionally preserve or re-raise Cats MTL's internal transport error.

## References
- Load `references/custom-error-types.md` for checked Scala 3/2 samples, source notes, Cats Effect interactions, and review prompts.
