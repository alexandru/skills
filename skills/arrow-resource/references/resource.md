# Arrow Resource (Kotlin) - Practical Guide

Concise reference for Arrow `Resource` and `resourceScope`, based on Arrow docs and common usage patterns.

## Core model
- `typealias Resource<A> = suspend ResourceScope.() -> A`
- Three phases: acquire -> use -> release.
- `ExitCase` tells the release phase why it runs: Completed, Failure, Cancelled.
- Acquisition and release run in `NonCancellable`.

## Core APIs
- `resource { ... }` creates a Resource recipe.
- `resourceScope { ... }` executes resources and guarantees release.
- `install(acquire) { resource, exitCase -> release }` registers a finalizer.
- `.bind()` inside `resourceScope` or `resource` to acquire a Resource.
- JVM interop: `closeable` wraps `AutoCloseable` safely.

## When to use Resource
- Need suspend finalizers.
- Need MPP-compatible resource management.
- Want composable acquisition and release with structured concurrency.

## Patterns

### 1) Resource constructors
Create reusable constructors on `ResourceScope`:

```kotlin
import arrow.fx.coroutines.ResourceScope
import arrow.fx.coroutines.install

class UserProcessor {
  fun start() {}
  fun shutdown() {}
}

suspend fun ResourceScope.userProcessor(): UserProcessor =
  install({ UserProcessor().also { it.start() } }) { p, _ -> p.shutdown() }
```

Use as a `Resource` value when you want a recipe:

```kotlin
import arrow.fx.coroutines.Resource
import arrow.fx.coroutines.resource

val userProcessor: Resource<UserProcessor> = resource { userProcessor() }
```

### 2) Composing resources

```kotlin
import arrow.fx.coroutines.resource

class DataSource { fun connect() {}; fun close() {} }
class Service(val ds: DataSource, val processor: UserProcessor)

val dataSource: Resource<DataSource> = resource({ DataSource().also { it.connect() } }) { ds, _ -> ds.close() }
val service: Resource<Service> = resource { Service(dataSource.bind(), userProcessor.bind()) }
```

### 3) Parallel acquisition

```kotlin
import arrow.fx.coroutines.resourceScope
import arrow.fx.coroutines.parZip

suspend fun example(): Unit = resourceScope {
  val service = parZip({ userProcessor() }, { dataSource.bind() }) { p, ds -> Service(ds, p) }
  service.processData()
}
```

### 4) Temp file with cleanup

```kotlin
import arrow.fx.coroutines.Resource
import arrow.fx.coroutines.resource
import java.io.File

fun tempFileResource(prefix: String, suffix: String? = null): Resource<File> = resource {
  install(
    { File.createTempFile(prefix, suffix) },
    { file, _ -> if (file.exists()) file.delete() }
  )
}
```

### 5) Kotlin `Source` (or stream-like) resource

```kotlin
import arrow.fx.coroutines.Resource
import arrow.fx.coroutines.resource
import kotlinx.io.Source
import kotlinx.io.buffered
import kotlinx.io.files.Path
import kotlinx.io.files.SystemFileSystem

fun fileSourceResource(path: String): Resource<Source> = resource {
  install(
    { SystemFileSystem.source(Path(path)).buffered() },
    { source, _ -> source.close() }
  )
}
```

### 6) Database pool + per-connection resource

```kotlin
import arrow.fx.coroutines.Resource
import arrow.fx.coroutines.resource
import javax.sql.DataSource

class Pool : AutoCloseable { override fun close() {} }

fun poolResource(): Resource<Pool> = resource(
  { Pool() },
  { pool, _ -> pool.close() }
)

fun connectionResource(ds: DataSource): Resource<java.sql.Connection> = resource(
  { ds.connection },
  { c, _ -> c.close() }
)
```

### 7) Multipart part disposal

```kotlin
import arrow.fx.coroutines.Resource
import arrow.fx.coroutines.resource

interface Part { fun dispose() }

fun partResource(part: Part): Resource<Part> = resource {
  onClose { part.dispose() }
  part
}
```

## Typed errors integration
- `resourceScope` can wrap an `either` block or be nested inside it.
- Nesting order changes the `ExitCase` observed by finalizers, but release always runs.
- Choose nesting order based on how you want finalizers to interpret early exits.

## Checklist
- Make release idempotent.
- Decide which `ExitCase` values require compensating actions.
- Prefer composing Resource values over deep nesting of `install` calls.
