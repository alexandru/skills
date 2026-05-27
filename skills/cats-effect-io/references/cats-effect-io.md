# Cats Effect IO and Typeclasses (Scala)

Sources:
- https://typelevel.org/cats-effect/docs/tutorial
- https://typelevel.org/cats-effect/docs/concepts
- https://typelevel.org/cats-effect/docs/recipes
- https://typelevel.org/cats-effect/docs/faq
- https://typelevel.org/cats-effect/docs/core/test-runtime
- https://rockthejvm.com/articles/cats-effect-3-racing-ios
- https://rockthejvm.com/articles/cats-effect-3-introduction-to-fibers
- https://openjdk.org/jeps/444

## Table of Contents
- [Core ideas](#core-ideas)
- [Side-effect discipline](#side-effect-discipline)
- [Choosing capabilities](#choosing-capabilities)
- [Blocking and interruptibility](#blocking-and-interruptibility)
- [Resource and factory safety](#resource-and-factory-safety)
- [Fibers, races, and structured concurrency](#fibers-races-and-structured-concurrency)
- [Execution boundary rules](#execution-boundary-rules)
- [Common recipes](#common-recipes)
- [API samples](#api-samples)
- [Testing guidance](#testing-guidance)
- [FAQ highlights](#faq-highlights)
- [Verification](#verification)

## Core ideas
- **Effects as values**: `IO[A]` (or `F[A]`) describes side effects; nothing runs until the effect is evaluated.
- **Fibers** are lightweight, passive descriptions of running effects. Starting a fiber is itself effectful and returns `IO[Fiber[...]]`.
- **Cancelation** is cooperative and always runs finalizers; use `Resource` to ensure cleanup under success, error, or cancel.
- **Asynchronous vs synchronous**: `IO.async` uses callbacks; `IO.delay`/`IO.blocking`/`IO.interruptible` use synchronous execution.

## Side-effect discipline
- Suspend every side effect at the call site. Do not compute a value first and then wrap the already-computed value.
- Time and randomness are side effects: prefer `Clock[F]`/`Random[F]` when they fit, or `Sync[F].delay(...)`/`IO(...)` at the edge.
- Mutable identity is a side effect when it can escape. Allocate `Array`, mutable collections, atomics, and caches inside `IO`/`F`/`Resource` factories.
- Constructors should not allocate shared mutable state, start fibers, read configuration, open resources, or sample time/randomness. Use `create`/`resource` constructors.
- Local mutation is acceptable for implementation efficiency only when the whole block is suspended and no mutable value escapes.

## Choosing capabilities
- Use plain pure functions for deterministic business logic.
- Use `Clock[F]` for time reads and `Random[F]` for random values when possible.
- Use `Sync[F]` for synchronous side effects, interruptible/blocking calls, `Ref.of`, and mutable factory allocation.
- Use `Async[F]` for callback APIs and async registration.
- Use `Temporal[F]` for `sleep`, timeouts, and retry timing.
- Use `Concurrent[F]` or stronger when starting fibers, racing effects, or using concurrent primitives such as `Deferred`, `Queue`, and `Semaphore`.

## Blocking and interruptibility
- Prefer `IO.interruptible`/`Sync[F].interruptible` for blocking use-phase calls. It runs on the blocking pool and gives cancellation a chance to interrupt the underlying thread.
- Do not make agents prove that each Java API honors interruption before choosing `interruptible`; that is not practical, and modern JDKs have made more blocking APIs interruption-aware. JEP 444 specifies that socket blocking I/O on virtual threads is interruptible and wakes by closing the socket.
- Some APIs still ignore interruption or only observe it in specific runtime contexts. If cancellation responsiveness matters and interruption is not enough, add an explicit cancellation protocol such as closing the underlying resource.
- Use `IO.blocking`/`Sync[F].blocking` for acquisition, cleanup, and finalizers, especially `Closeable#close`/`AutoCloseable#close`.

## Resource and factory safety
- Prefer `Resource` over manual `try/finally` for acquisition/release.
- Use `Resource.fromAutoCloseable` for simple `AutoCloseable` lifecycles; use `Resource.make` when you need custom release handling.
- For stateful services, expose `def create[F[_]: Sync]: F[Service]` or `def resource[F[_]: Sync]: Resource[F, Service]`. Pass the created service as a dependency.
- Do not publish raw mutable values such as `Array` or `AtomicReference` unless mutation is part of a deliberately effectful API.

## Fibers, races, and structured concurrency
- Prefer structured combinators (`parTraverse`, `parMapN`, `Supervisor`, `background`, `Resource`) before manual `start`.
- If you use `start`, always join, cancel, or supervise the fiber. `Fiber#join` returns an `Outcome`, not the raw value.
- `IO.race(a, b)` cancels the loser. Use it for timeout-like patterns where loser cancelation is correct.
- `IO.racePair(a, b)` returns the winning `Outcome` and the losing `Fiber`; you must decide what to do with the loser.
- Add `onCancel` cleanup only for cleanup local to that effect. Resource finalizers are the primary lifecycle cleanup mechanism.

## Execution boundary rules
- Treat `unsafeRun*` as a runtime-boundary operation only; application and test code should not call it.
- `import cats.effect.unsafe.implicits.global` is banned.
- Keep effect execution at framework boundaries (`IOApp`, http server runtimes, stream runtimes).
- To bridge non-Cats-Effect callback APIs, use `Dispatcher`.

## Common recipes
- **Dispatcher provisioning**: resource-scoped components may create and use their own `Dispatcher` inside that same `Resource`; otherwise require `Dispatcher` as a parameter (`using`/implicit is fine).
- **Background work**: use `Supervisor` for start-and-forget fibers with safe cleanup.
- **Effectful loops**: use `traverse`/`traverse_` and `parTraverse` for sequencing or parallelism.
- **Shared state**: use `Ref`, `Deferred`, and other std primitives. Allocate these primitives in `F` and pass them as dependencies.
- **Akka Streams or Future interop**: keep `unsafeToFuture` inside the bridge function and require a `Dispatcher[IO]`; do not import an unsafe runtime.

## API samples

These samples are represented in `scripts/verify-examples.scala`.

Side effects as values:
```scala
import cats.effect.{Clock, IO, Sync}
import cats.effect.std.Random
import cats.syntax.all.*

import java.time.Instant

def nowIO: IO[Instant] =
  IO(Instant.now())

def nowF[F[_]: Sync]: F[Instant] =
  Sync[F].delay(Instant.now())

def clockNow[F[_]: Clock]: F[Instant] =
  Clock[F].realTimeInstant

def randomInt[F[_]: Sync]: F[Int] =
  Random.scalaUtilRandom[F].flatMap(_.nextInt)
```

Effectful factories for mutable state:
```scala
import cats.effect.{IO, Ref, Sync}

final class Scratch private (private val buffer: Array[Byte]) {
  def size: Int = buffer.length
}

object Scratch {
  def create[F[_]: Sync](size: Int): F[Scratch] =
    Sync[F].delay(new Scratch(new Array[Byte](size)))
}

final class Counter private (ref: Ref[IO, Int]) {
  def next: IO[Int] =
    ref.updateAndGet(_ + 1)
}

object Counter {
  def create: IO[Counter] =
    Ref.of[IO, Int](0).map(new Counter(_))
}
```

Blocking, resources, and interruptible calls:
```scala
import cats.effect.{IO, Resource, Sync}

import java.io.FileInputStream
import java.nio.file.Path

def inputStream(path: Path): Resource[IO, FileInputStream] =
  Resource.fromAutoCloseable(IO.blocking(new FileInputStream(path.toFile)))

def readFirstByte(path: Path): IO[Int] =
  inputStream(path).use(in => IO.interruptible(in.read()))

def interruptibleSleep[F[_]: Sync]: F[Unit] =
  Sync[F].interruptible(Thread.sleep(250))
```

Fibers and races:
```scala
import cats.effect.{IO, Outcome}
import cats.syntax.all.*

import scala.concurrent.duration.*

def fromOutcome[A](outcome: Outcome[IO, Throwable, A]): IO[A] =
  outcome match {
    case Outcome.Succeeded(fa) => fa
    case Outcome.Errored(e)    => IO.raiseError(e)
    case Outcome.Canceled()    => IO.canceled *> IO.never[A]
  }

def startAndJoin[A](ioa: IO[A]): IO[A] =
  ioa.start.flatMap(_.join).flatMap(fromOutcome)

def timeoutToOption[A](ioa: IO[A], limit: FiniteDuration): IO[Option[A]] =
  IO.race(ioa, IO.sleep(limit)).map {
    case Left(value) => Some(value)
    case Right(_)    => None
  }

def fastest[A](left: IO[A], right: IO[A]): IO[A] =
  IO.racePair(left, right).flatMap {
    case Left((winner, loser))  => loser.cancel *> fromOutcome(winner)
    case Right((loser, winner)) => loser.cancel *> fromOutcome(winner)
  }
```

Structured concurrency:
```scala
import cats.effect.IO
import cats.syntax.all._

def parallelPrint: IO[Unit] =
  (IO.println("A"), IO.println("B")).parTupled.void
```

Dispatcher bridge:
```scala
import cats.effect.IO
import cats.effect.std.Dispatcher

import scala.concurrent.Future

def toFutureCallback(using dispatcher: Dispatcher[IO]): String => Future[Unit] =
  message => dispatcher.unsafeToFuture(IO.println(message))
```

## Testing guidance
- Prefer test frameworks/modules that accept effectful tests (`IO[Assertion]`, `F[Assertion]`) instead of manual `unsafeRun*`.
- Avoid real sleeping in unit tests. Use virtual time with `TestControl` for deterministic scheduling.
- `SyncIO` can be lifted without running it: `val io: IO[A] = syncIo.to[IO]`.

Virtual-time test example:
```scala
import cats.effect.IO
import cats.effect.testkit.TestControl
import cats.syntax.all.*

import scala.concurrent.duration._

def virtualTimeResult: IO[Int] =
  TestControl.executeEmbed(IO.sleep(1.second) *> IO.pure(42))
```

## FAQ highlights
- If an `IO` is created but not composed, it does not run; compiler warnings can help catch this.
- `IO(...)` may run on a blocking thread in some optimized cases; this is normal.
- Starvation warnings often indicate accidental blocking without `IO.blocking`.
- `IO.blocking(...).timeout(...)` waits for the blocking operation; use `interruptible` for blocking use-phase calls when timeout/cancel responsiveness matters.
- For Scala CLI, put Cats Effect applications in an `IOApp` in a `.scala` file rather than using `unsafeRunSync` in a script.

## Verification
- Representative examples compile in `scripts/verify-examples.scala` with Scala 3, Cats Effect 3.7.0, `cats-effect-testkit`, and `-no-indent`.
