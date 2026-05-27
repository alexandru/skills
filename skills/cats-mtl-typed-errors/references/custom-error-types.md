# Cats MTL Typed Errors: Checked Examples and Review Guidance

Sources:
- https://typelevel.org/blog/2025/09/02/custom-error-types.html (canonical content: https://typelevel.org/blog/custom-error-types.html)
- https://typelevel.org/cats-mtl/mtl-classes/raise.html
- https://typelevel.org/cats-mtl/mtl-classes/handle.html

This reference was checked with Scala `3.3.7`, Scala `2.13.16`, Cats MTL `1.6.0`, and Cats Effect `3.7.0`. The examples are represented by:
- `scripts/verify-examples.scala`
- `scripts/verify-examples-scala2.scala`

## Contents
- [Mental model](#mental-model)
- [Scala 3 workflow](#scala-3-workflow)
- [Pure Either tests](#pure-either-tests)
- [IO-specific APIs](#io-specific-apis)
- [Local recovery with Handle](#local-recovery-with-handle)
- [Composing error domains](#composing-error-domains)
- [Scala 2 syntax](#scala-2-syntax)
- [Cats Effect interactions](#cats-effect-interactions)
- [Review checklist](#review-checklist)
- [Representative prompts](#representative-prompts)

## Mental model

Cats Effect `IO[A]` has one runtime error channel: `Throwable`. Cats MTL `Raise[F, E]` adds a scoped capability for domain errors of type `E` without changing `IO` into a bifunctor and without forcing `EitherT`.

Use these roles consistently:
- `Raise[F, E]`: the function may raise typed domain error `E`.
- `Handle[F, E]`: the function may raise and recover from `E`.
- `Handle.allow`/`rescue` or `Handle.allowF`/`rescue`: introduce and close a lexical typed-error scope.
- `Either[E, A]`: pure boundary or test interpreter, not the default shape for effectful Cats Effect workflows.

## Scala 3 workflow

Import Cats, Cats Effect, Cats MTL, and syntax once near the module boundary:

```scala
import cats.{Applicative, Monad}
import cats.effect.{IO, IOApp}
import cats.mtl.{Handle, Raise}
import cats.mtl.syntax.all.*
import cats.syntax.all.*
```

Model focused domain errors and keep the raising function honest about its capabilities. `Applicative` is enough when the function only needs `pure` and `raise`.

```scala
final case class Result(value: String)

enum ParseError:
  case BlankInput
  case MissingSemicolon(input: String)

def parse[F[_]](input: String)(using Raise[F, ParseError], Applicative[F]): F[Result] =
  val trimmed = input.trim
  if trimmed.isEmpty then
    ParseError.BlankInput.raise[F, Result]
  else if !trimmed.endsWith(";") then
    ParseError.MissingSemicolon(input).raise
  else
    Result(trimmed.dropRight(1)).pure[F]
```

Handle the domain error at a real boundary. Keep the `rescue` cases exhaustive for the error ADT and translate the error into the boundary result.

```scala
def parseProgram(input: String): IO[String] =
  Handle.allow[ParseError]:
    parse[IO](input).map(result => s"parsed ${result.value}")
  .rescue:
    case ParseError.BlankInput =>
      IO.pure("empty input")
    case ParseError.MissingSemicolon(text) =>
      IO.pure(s"missing semicolon in $text")
```

## Pure Either tests

The same `Raise`-based function can run in pure tests by instantiating `F` as `Either[E, *]`. Prefer a named type alias in Scala 3 samples so code remains clear without extra compiler plugin syntax.

```scala
type ParseEither[A] = Either[ParseError, A]

def parseEither(input: String): Either[ParseError, Result] =
  parse[ParseEither](input)
```

## IO-specific APIs

`F[_]` polymorphism is optional. When a codebase uses concrete `IO`, require `Raise[IO, E]` directly and keep all Cats Effect side-effect rules from the `cats-effect-io` skill.

```scala
def parseIoOnly(input: String)(using Raise[IO, ParseError]): IO[Result] =
  parse[IO](input)
```

Use `F[_]` when it buys testability or reuse; otherwise concrete `IO` plus `Raise[IO, E]` is fine.

## Local recovery with Handle

Use `Handle[F, E]` only where recovery is part of the function's contract. Most domain functions should require only `Raise[F, E]`.

```scala
def parseOrFallback[F[_]](input: String)(using Handle[F, ParseError], Applicative[F]): F[Result] =
  parse[F](input).handle[ParseError] {
    case ParseError.BlankInput             => Result("default")
    case ParseError.MissingSemicolon(text) => Result(text.trim)
  }
```

## Composing error domains

Do not make sealed error hierarchies inherit from each other. Compose error domains with wrapper cases so each ADT remains focused.

```scala
enum AppError:
  case Parse(error: ParseError)
  case MissingConfig(key: String)

def loadConfig[F[_]](key: String)(using Raise[F, AppError], Applicative[F]): F[String] =
  if key == "script" then "println;".pure[F]
  else AppError.MissingConfig(key).raise

def parseConfigured[F[_]](key: String)(using Raise[F, AppError], Monad[F]): F[Result] =
  loadConfig[F](key).flatMap { source =>
    parseEither(source).fold(
      error => AppError.Parse(error).raise[F, Result],
      result => result.pure[F]
    )
  }
```

The boundary handles the outer domain:

```scala
def appProgram(key: String): IO[String] =
  Handle.allow[AppError]:
    parseConfigured[IO](key).map(_.value)
  .rescue:
    case AppError.Parse(ParseError.BlankInput) =>
      IO.pure("configured script was blank")
    case AppError.Parse(ParseError.MissingSemicolon(_)) =>
      IO.pure("configured script was incomplete")
    case AppError.MissingConfig(missingKey) =>
      IO.pure(s"missing config: $missingKey")
```

## Scala 2 syntax

Scala 2 uses explicit implicits and `allowF`. Keep the same capability design.

```scala
import cats.Applicative
import cats.effect.{IO, IOApp}
import cats.mtl.{Handle, Raise}
import cats.mtl.syntax.all._
import cats.syntax.all._

object Scala2Sample {
  final case class Result(value: String)

  sealed trait ParseError extends Product with Serializable
  object ParseError {
    case object BlankInput extends ParseError
    final case class MissingSemicolon(input: String) extends ParseError
  }

  def parse[F[_]](input: String)(implicit r: Raise[F, ParseError], a: Applicative[F]): F[Result] = {
    val trimmed = input.trim
    if (trimmed.isEmpty)
      ParseError.BlankInput.raise[F, Result]
    else if (!trimmed.endsWith(";"))
      ParseError.MissingSemicolon(input).raise[F, Result]
    else
      Result(trimmed.dropRight(1)).pure[F]
  }

  val program: IO[String] =
    Handle.allowF[IO, ParseError] { implicit h =>
      parse[IO]("ok;").map(result => s"parsed ${result.value}")
    } rescue {
      case ParseError.BlankInput =>
        IO.pure("empty input")
      case ParseError.MissingSemicolon(text) =>
        IO.pure(s"missing semicolon in $text")
    }
}
```

## Cats Effect interactions

Cats MTL's scoped errors travel through the single `Throwable` channel internally and are caught by the `rescue` boundary. That is why they preserve normal Cats Effect composition around resources, fibers, Fs2, Http4s, and generic `F[_]` libraries.

Review these interactions carefully:
- Do not add `EitherT` around Cats Effect code only to obtain a typed domain error channel.
- Do not catch broad `Throwable` inside an `allow` scope unless the code intentionally preserves or re-raises the internal transport error.
- Keep resource acquisition, release, blocking, cancellation, and fiber usage governed by Cats Effect rules. This skill only models expected domain failures.
- Use exceptions for unexpected faults, Java/OOP interop, or implementation details that should not become public domain failures.

## Review checklist

- The error ADT is focused and does not extend `Throwable` just to fit `IO.raiseError`.
- Functions that only raise require `Raise[F, E]`, not `Handle[F, E]`, `MonadError[F, Throwable]`, or `Async[F]`.
- Constraints are minimal: `Applicative` for `pure` and `raise`, `Monad` for sequencing, Cats Effect typeclasses for side effects.
- `allow`/`allowF` appears at a meaningful boundary and `rescue` handles the full domain.
- Lower-level errors are wrapped into higher-level errors instead of modeled with sealed-on-sealed inheritance.
- Pure validation/test code may use `Either`; effectful Cats Effect workflows do not expose `IO[Either[E, A]]` unless that is an explicit API boundary.
- New or changed Scala snippets are represented in the skill-local verification scripts and have been run.

## Representative prompts

- Replace an `EitherT[IO, E, A]` service flow with Cats MTL `Raise` and an `allow`/`rescue` boundary.
- Refactor a sealed-on-sealed domain error hierarchy into wrapper cases.
- Add typed parse errors to a Cats Effect route without losing `Resource` and fiber semantics.
- Convert a pure `Either` validator into a `Raise[F, E]` function and keep an `Either` interpreter for tests.
