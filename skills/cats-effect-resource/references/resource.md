# Cats Effect Resource (Scala) - Practical Guide

Sources:
- https://typelevel.org/cats-effect/docs/std/resource
- https://github.com/typelevel/cats-effect/blob/series/3.x/kernel/shared/src/main/scala/cats/effect/kernel/Resource.scala

## Table of Contents
- [Core model](#core-model)
- [Core APIs](#core-apis)
- [When to use Resource](#when-to-use-resource)
- [No leaking](#no-leaking)
- [Class and factory design](#class-and-factory-design)
- [Patterns](#patterns)
- [Cancelation and error behavior](#cancelation-and-error-behavior)
- [Interop and blocking](#interop-and-blocking)
- [Advanced APIs](#advanced-apis)
- [Checklist](#checklist)
- [Verification](#verification)

## Core model
- `Resource[F, A]` is a recipe for acquiring `A` and registering finalizers, not an already-open handle.
- `.use` acquires the resource, runs an `A => F[B]`, then releases the resource as soon as that use action completes.
- Release runs on success, failure, or cancelation.
- Nested resources release in reverse acquisition order (LIFO); outer resources release even if inner acquisition/use/release fails.
- `Resource.make` acquire and release actions are not interruptible. `Resource.eval` preserves the interruptibility of the lifted effect.
- Calling `.use` twice acquires twice. To share one acquired handle, run all operations inside one `.use`.

## Core APIs
- `Resource.make(acquire)(release)` for custom lifecycle.
- `Resource.makeCase(acquire)((a, exitCase) => release)` when cleanup depends on success, error, or cancelation.
- `Resource.fromAutoCloseable` for `AutoCloseable` lifecycles.
- `Resource.eval` to lift an effect into a resource.
- `.use` to run the resource and ensure release.
- `.useForever` for resource-shaped applications that run until canceled.
- `map`, `flatMap`, `mapN`, `parMapN`, `parZip` to compose resources.

## When to use Resource
- You need safe cleanup under cancelation.
- You need to compose resources and guarantee LIFO release.
- You want an API that makes lifecycle explicit and testable.
- You are constructing a class or service that owns a file, stream, socket, client, pool, background fiber, cache, lock, or any `AutoCloseable`.
- You are wrapping Java APIs whose allocation and cleanup are side effects.

## No leaking
Never return an acquired resource handle from `.use`; the handle is already released when the caller receives it.

```scala
import cats.effect.{IO, Resource, Sync}

import java.io.BufferedReader
import java.nio.file.{Files, Path}

def bufferedReader[F[_]: Sync](path: Path): Resource[F, BufferedReader] =
  Resource.fromAutoCloseable(Sync[F].blocking(Files.newBufferedReader(path)))

def leakedClosedReader(path: Path): IO[BufferedReader] =
  bufferedReader[IO](path).use(IO.pure)

def firstLine(path: Path): IO[Option[String]] =
  bufferedReader[IO](path).use { reader =>
    IO.interruptible(Option(reader.readLine()))
  }
```

Also avoid returning objects that merely hide the released handle. If a service contains a file handle, DB connection, pool, or client acquired by `Resource`, the service value must stay inside the `.use` scope.

## Class and factory design
Classes should receive already-acquired dependencies through constructors. Companion objects or module factories own acquisition and return `Resource`.

```scala
import cats.effect.{IO, Resource, Sync}
import cats.syntax.all.*

import java.io.BufferedReader
import java.nio.file.{Files, Path}

final class UserProcessor private () {
  private var running: Boolean = false

  private def start(): Unit =
    running = true

  private def shutdown(): Unit =
    running = false

  def process[F[_]: Sync](line: String): F[String] =
    Sync[F].delay {
      if (!running) throw new IllegalStateException("processor is shut down")
      line.trim.toUpperCase
    }
}

object UserProcessor {
  def resource[F[_]: Sync]: Resource[F, UserProcessor] =
    Resource.make {
      Sync[F].delay {
        val processor = new UserProcessor
        processor.start()
        processor
      }
    } { processor =>
      Sync[F].delay(processor.shutdown())
    }
}

final class ReportService[F[_]: Sync] private (
    processor: UserProcessor,
    reader: BufferedReader
) {
  def firstProcessedLine: F[Option[String]] =
    Sync[F].interruptible(reader.readLine()).flatMap {
      case null => Sync[F].pure(None)
      case line => processor.process[F](line).map(Some(_))
    }
}

object ReportService {
  private def reportReader[F[_]: Sync](path: Path): Resource[F, BufferedReader] =
    Resource.fromAutoCloseable(Sync[F].blocking(Files.newBufferedReader(path)))

  def resource[F[_]: Sync](path: Path): Resource[F, ReportService[F]] =
    (UserProcessor.resource[F], reportReader[F](path)).mapN { (processor, reader) =>
      new ReportService[F](processor, reader)
    }
}

def runReport(path: Path): IO[Option[String]] =
  ReportService.resource[IO](path).use(_.firstProcessedLine)
```

Bad patterns:
- Public constructors that open files, sockets, pools, or clients.
- Constructors that accept `Resource[F, A]` and call `.use` internally for each method call when the class is meant to share one acquired handle.
- Top-level vals or lazy vals that allocate disposable resources.
- Methods that expose raw `BufferedReader`, connection, client, or pool handles to callers after the resource scope.

## Patterns

### 1) Resource constructors
Prefer functions that return `Resource[F, A]`:

```scala
import cats.effect.{Resource, Sync}

final class LifecycleProcessor {
  def start(): Unit = ()
  def shutdown(): Unit = ()
}

def lifecycleProcessor[F[_]: Sync]: Resource[F, LifecycleProcessor] =
  Resource.make {
    Sync[F].delay {
      val processor = new LifecycleProcessor
      processor.start()
      processor
    }
  } { processor =>
    Sync[F].delay(processor.shutdown())
  }
```

### 2) Composing resources

```scala
import cats.effect.{Resource, Sync}
import cats.syntax.all._

final class ConfigSource { def connect(): Unit = (); def close(): Unit = () }
final class ComposedService(ds: ConfigSource, processor: LifecycleProcessor)

def configSource[F[_]: Sync]: Resource[F, ConfigSource] =
  Resource.make {
    Sync[F].delay {
      val ds = new ConfigSource
      ds.connect()
      ds
    }
  } { ds =>
    Sync[F].delay(ds.close())
  }

def composedService[F[_]: Sync]: Resource[F, ComposedService] =
  (configSource[F], lifecycleProcessor[F]).mapN(new ComposedService(_, _))
```

### 3) Parallel acquisition

```scala
import cats.effect.{Concurrent, Resource, Sync}
import cats.syntax.all._

def servicePar[F[_]: Concurrent: Sync]: Resource[F, ComposedService] =
  (configSource[F], lifecycleProcessor[F]).parMapN(new ComposedService(_, _))
```

### 4) File input stream

```scala
import cats.effect.{IO, Resource}

import java.io.FileInputStream

def fileInputStreamIO(path: String): Resource[IO, FileInputStream] =
  Resource.fromAutoCloseable(IO.blocking(new FileInputStream(path)))
```

### 5) Database pool + per-connection resource

```scala
import cats.effect.{Resource, Sync}

trait DbPool extends AutoCloseable {
  def getConnection: java.sql.Connection
}

def pool[F[_]: Sync](open: F[DbPool]): Resource[F, DbPool] =
  Resource.fromAutoCloseable(open)

def connection[F[_]: Sync](db: DbPool): Resource[F, java.sql.Connection] =
  Resource.make(Sync[F].blocking(db.getConnection))(c =>
    Sync[F].blocking(c.close())
  )
```

### 6) Acquire in a loop
Use `Resource.make` per element and compose with `traverse`/`parTraverse`:

```scala
import cats.effect.{Resource, Sync}
import cats.syntax.all._

final class Handle(id: String) {
  def close(): Unit = ()
}

def acquireOne[F[_]: Sync](id: String): Resource[F, Handle] =
  Resource.make(Sync[F].delay(new Handle(id)))(handle =>
    Sync[F].delay(handle.close())
  )

def acquireAll[F[_]: Sync](ids: List[String]): Resource[F, List[Handle]] =
  ids.traverse(acquireOne[F])
```

### 7) Exit-aware finalization
Use `makeCase` when release behavior depends on why the scope ended.

```scala
import cats.effect.{Ref, Resource, Sync}

def auditScope[F[_]: Sync](events: Ref[F, List[String]]): Resource[F, Unit] =
  Resource.makeCase(Sync[F].unit) { (_, exitCase) =>
    events.update(exitCase.toString :: _)
  }
```

## Cancelation and error behavior
- Finalizers run on success, error, or cancelation.
- If finalizers can fail, decide whether to log, suppress, or raise secondary errors.
- Keep finalizers idempotent and minimal to avoid cascading failures during release.
- If acquisition fails before a value is acquired, that resource's release does not run; already-acquired outer resources still release.
- Use `makeCase` or `onFinalizeCase` when exit case matters.
- Use `makeFull`/`makeCaseFull` only for advanced cancelable-acquire cases; if acquisition can be canceled after partial allocation, the acquire action must clean up its partial state.

## Interop and blocking
- Wrap blocking acquisition in `Sync[F].blocking`/`IO.blocking` to avoid compute starvation.
- Prefer `IO.interruptible`/`Sync[F].interruptible` for blocking use-phase operations inside `.use`.
- Prefer `Resource.fromAutoCloseable(Sync[F].blocking(...))` for Java interop; its close action runs in the blocking context.
- Use `Resource.make` for custom release, extra logging, custom error handling, or non-`AutoCloseable` APIs.
- If the API supports cooperative cancellation, combine it with `Resource` to ensure cleanup.
- For `Closeable#close`/`AutoCloseable#close`, use `blocking`, not `interruptible`.

```scala
import cats.effect.{IO, Resource, Sync}

import java.io.FileInputStream
import java.nio.file.Path

def fileInputStreamResource[F[_]: Sync](path: Path): Resource[F, FileInputStream] =
  Resource.fromAutoCloseable(Sync[F].blocking(new FileInputStream(path.toFile)))

def readFirstByteViaResource(path: Path): IO[Int] =
  fileInputStreamResource[IO](path).use(stream => IO.interruptible(stream.read()))
```

## Advanced APIs
- `allocated`/`allocatedCase` return the acquired value plus a finalizer. They are advanced and can leak resources if the finalizer is not called exactly once.
- Prefer `.use`; reach for `allocated` only when integrating with APIs that require separate setup/teardown.

```scala
import cats.effect.IO
import cats.syntax.all.*

import java.nio.file.Path

def allocatedSafely(path: Path): IO[Option[String]] =
  ReportService.resource[IO](path).allocated.flatMap { case (service, release) =>
    service.firstProcessedLine.guarantee(release)
  }
```

## Checklist
- Expose `Resource[F, A]` in public constructors.
- Never return raw acquired handles from `.use`.
- Keep acquired services inside the `.use` scope unless their finalizer is managed elsewhere.
- Put all disposable allocations in `Resource`, including Java `AutoCloseable` values.
- Make classes accept acquired dependencies; put resource acquisition in companion/factory methods.
- Keep release idempotent and tolerant of partial failures.
- Use `parMapN` only for independent resources.
- Avoid calling `.use` except at lifecycle boundaries.
- Use `IO.blocking`/`Sync[F].blocking` for blocking acquisition/release and `IO.interruptible`/`Sync[F].interruptible` for blocking use-phase operations.

## Verification
- Representative examples compile in `scripts/verify-examples.scala` with Scala 3, Cats Effect 3.7.0, and `-no-indent`.
