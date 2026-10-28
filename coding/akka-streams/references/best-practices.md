# Akka Streams: Best Practices and Warnings

Sources:
- https://doc.akka.io/libraries/akka-core/current/general/stream/stream-design.html
- https://alexn.org/blog/2023/04/17/integrating-akka-with-cats-effect-3/

## Table of Contents

- [Critical: When NOT to Use Streams](#critical-when-not-to-use-streams)
- [When Streams ARE Appropriate](#when-streams-are-appropriate)
- [Design Principles](#design-principles)
- [Common Anti-Patterns](#common-anti-patterns)
- [Resource Cleanup](#resource-cleanup)
- [Materialized Values](#materialized-values)
- [Testing Philosophy](#testing-philosophy)
- [Supervision Strategies](#supervision-strategies)
- [Pekko Streams Notes](#pekko-streams-notes)

## Critical: When NOT to Use Streams

### Use plain functions instead
Streams are not a replacement for regular data transformations. If you can express your logic as pure functions, do so:

**Bad** (unnecessary stream complexity):
```scala
val stream = Source(List(1, 2, 3, 4, 5))
  .map(_ * 2)
  .filter(_ > 5)
  .runWith(Sink.seq)
```

**Good** (simple functional code):
```scala
val result = List(1, 2, 3, 4, 5)
  .map(_ * 2)
  .filter(_ > 5)
```

### Use plain functions for I/O
Despite Akka's documentation suggesting streams for I/O, **prefer plain functions or other abstractions**:

**Bad** (streams for simple I/O):
```scala
Source.fromIterator(() => lines.iterator)
  .map(processLine)
  .runWith(Sink.foreach(println))
```

**Good** (plain functions):
```scala
lines.foreach { line =>
  val result = processLine(line)
  println(result)
}
```

Or with an effect system for better composition:
```scala
import cats.effect.IO

lines.traverse_(line => 
  IO(processLine(line)).flatMap(result => IO.println(result))
)
```

Streams couple processing with execution, making testing and composition harder.

### Integration challenges
If you must integrate Cats Effect with Akka Streams, be aware of challenges:
- Cancellation semantics differ (cooperative vs. immediate)
- Resource safety requires careful `Resource` and `Stream` composition
- Backpressure bridging is non-trivial
- See: https://alexn.org/blog/2023/04/17/integrating-akka-with-cats-effect-3/

## When Streams ARE Appropriate

Use Akka Streams for dataflow and reactive programming patterns:

1. **Dataflow programming** - expressing computation as a graph of operations
2. **Reactive Streams interop** with other compliant libraries
3. **Complex graph topologies** with fan-out, fan-in, and rate control
4. **Integration with Akka actors** for distributed stream processing
5. **Backpressure management** between independent processing stages

Example valid use case:
```scala
// Processing messages from Kafka with bounded memory
Source
  .fromGraph(KafkaSource.committableSource(...))
  .mapAsync(parallelism = 4)(processMessage)
  .toMat(CommittableSink)(Keep.both)
  .run()
```

## Design Principles

### Supreme compositionality
Stream components should be reusable building blocks:

```scala
// Define reusable components
val validation: Flow[String, ValidData, NotUsed] = 
  Flow[String].map(validate).collect { case Valid(data) => data }

val processing: Flow[ValidData, Result, NotUsed] =
  Flow[ValidData].mapAsync(4)(process)

// Compose into larger graphs
Source(input)
  .via(validation)
  .via(processing)
  .runWith(Sink.seq)
```

### Explicit error handling
Never rely on default "tear down entire stream" behavior in production:

```scala
Source(1 to 10)
  .map(risky)
  .recover {
    case _: BusinessException => fallbackValue
  }
  .withAttributes(supervisionStrategy(resumingDecider))
```

### Immutable blueprints
Streams are immutable descriptions until materialized:

```scala
val blueprint = Source(1 to 10).map(_ * 2)

// Can reuse blueprint multiple times
val run1 = blueprint.runWith(Sink.seq)
val run2 = blueprint.runWith(Sink.head)
```

## Common Anti-Patterns

### Over-using streams for orchestration
Don't use streams as a poor man's workflow engine:

**Bad**:
```scala
Source.single(input)
  .mapAsync(1)(validateUser)
  .mapAsync(1)(checkPermissions)
  .mapAsync(1)(fetchData)
  .mapAsync(1)(transform)
  .runWith(Sink.head)
```

**Good** (use for-comprehension or flatMap):
```scala
for {
  user <- validateUser(input)
  _    <- checkPermissions(user)
  data <- fetchData(user)
  result <- transform(data)
} yield result
```

### Blocking in stream operators
Never block inside `map`, `mapAsync`, or other operators:

**Bad**:
```scala
Source(urls)
  .map { url =>
    // BLOCKING! Will starve the stream
    scala.io.Source.fromURL(url).mkString
  }
```

**Good**:
```scala
Source(urls)
  .mapAsync(4) { url =>
    Future {
      scala.io.Source.fromURL(url).mkString
    }(blockingEC) // Use dedicated blocking execution context
  }
```

### Ignoring backpressure
Don't use unbounded buffers to "solve" backpressure:

**Bad**:
```scala
source.buffer(Int.MaxValue, OverflowStrategy.backpressure)
```

**Good** (fix the rate mismatch):
```scala
source
  .throttle(100, 1.second)
  .buffer(1000, OverflowStrategy.backpressure)
```

## Resource Cleanup

Streams may drop elements on failure or cancellation; don't rely on stream completion for cleanup:

```scala
// Bad: assuming all elements will be processed
Source(resources)
  .map(r => r.close()) // May never run if stream fails

// Good: use Resource or bracket
Resource.fromAutoCloseable(IO(openResource))
  .use(r => processWithStreams(r))
```

## Materialized Values

Understand materialization produces runtime objects:

```scala
val (killSwitch, done) = 
  Source(...)
    .viaMat(KillSwitches.single)(Keep.right)
    .toMat(Sink.ignore)(Keep.both)
    .run()

// Use materialized values to control running stream
killSwitch.shutdown()
await(done)
```

## Testing Philosophy

- **Test components in isolation** before integration
- **Use TestKit** to control timing and backpressure
- **Test error scenarios** explicitly
- **Avoid testing implementation details** of Akka internals

See `references/testing.md` for comprehensive examples.

## Supervision Strategies

Three strategies for handling exceptions:

```scala
import akka.stream.Supervision._

val resumingDecider: Decider = {
  case _: BusinessException => Resume  // Skip element, continue
  case _: TransientError    => Restart // Restart operator
  case _                    => Stop    // Default: stop stream
}

source
  .map(risky)
  .withAttributes(supervisionStrategy(resumingDecider))
```

- **Resume**: skip failed element, continue processing
- **Restart**: reset operator state, continue from next element  
- **Stop**: tear down stream (default)

Choose based on whether failures are:
- **Element-specific** (Resume): bad data in one element
- **State-related** (Restart): operator state corrupted
- **Fatal** (Stop): unrecoverable error

## Pekko Streams Notes

Pekko is a fork of Akka 2.6.x maintained by the Apache Software Foundation. The API is identical except for package names:

- `akka.stream.*` → `org.apache.pekko.stream.*`
- `akka.actor.*` → `org.apache.pekko.actor.*`

All patterns, testing approaches, and best practices apply identically.
