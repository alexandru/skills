# Akka Streams and Pekko Streams

## Table of Contents
- [Core Concepts](#core-concepts)
- [Design Principles](#design-principles)
- [When NOT to Use Streams](#when-not-to-use-streams)
- [Best Practices](#best-practices)
- [Testing Stream Components](#testing-stream-components)
- [Common Patterns](#common-patterns)
- [Error Handling](#error-handling)
- [Backpressure and Rate Control](#backpressure-and-rate-control)
- [Working Examples](#working-examples)
- [Sources](#sources)

## Core Concepts

**Sources**:
- https://doc.akka.io/libraries/akka-core/current/general/stream/stream-design.html
- https://doc.akka.io/libraries/akka-core/current/stream/stream-flows-and-basics.html
- https://doc.akka.io/libraries/akka-core/current/stream/stream-testkit.html
- https://pekko.apache.org/docs/pekko/current/stream/

Akka Streams (and its fork, Pekko Streams) is an implementation of Reactive Streams for asynchronous stream processing with backpressure.

**Core abstractions**:
- `Source[Out, Mat]`: produces elements (0 to many), has one output.
- `Flow[In, Out, Mat]`: transforms elements, has one input and one output.
- `Sink[In, Mat]`: consumes elements, has one input.
- `RunnableGraph[Mat]`: fully connected stream that can be materialized and run.

**Materialization**: Running a stream produces a materialized value (`Mat`). The materialized value is separate from the stream elements and represents metadata like completion status, counters, or handles for control.

**Backpressure**: Downstream controls the rate of data flow; upstream respects demand signals to prevent overwhelming consumers.

## Design Principles

1. **Streams are values**: stream definitions are blueprints; nothing runs until materialized with `run()`.
2. **Composability**: combine small stream components (`Source`, `Flow`, `Sink`) to build complex pipelines.
3. **Backpressure by default**: all built-in operators respect backpressure; custom stages must too.
4. **Resource safety**: streams ensure cleanup on completion, failure, or cancellation.
5. **Locality of behavior**: stream stages operate independently; avoid shared mutable state.

## When NOT to Use Streams

**Avoid Akka Streams for**:
- **In-memory transformations on small collections**: use `List.map`, `filter`, etc. directly.
- **Single async results**: use `Future` instead of wrapping in a `Source.single`.
- **Operations that fit in pure functions**: don't create a `Flow` for what can be a simple `map`.
- **Synchronous, bounded data processing**: collections API is simpler and faster.

**Use Akka Streams when**:
- Processing unbounded or large datasets that don't fit in memory.
- Integrating async I/O sources (files, databases, HTTP, message queues).
- Backpressure is required to prevent resource exhaustion.
- Complex graph topologies are needed (fan-out, fan-in, cycles).

**Example of abuse** (DON'T do this):
```scala
// Bad: wrapping simple transformation in a stream
def doubleNumbers(numbers: List[Int]): Future[List[Int]] =
  Source(numbers)
    .map(_ * 2)
    .runWith(Sink.seq)

// Good: use collections directly
def doubleNumbers(numbers: List[Int]): List[Int] =
  numbers.map(_ * 2)
```

## Best Practices

### Component Design
- **Keep components small and reusable**: design `Flow` instances that do one thing well.
- **Type safety**: use specific types for `Source`, `Flow`, and `Sink` to catch errors at compile time.
- **Avoid side effects in stages**: prefer pure transformations in `map`/`filter`; use `mapAsync` for effects.
- **Materialized values**: choose meaningful materialized value types; use `Keep.right`, `Keep.left`, or `Keep.both` when combining.

### Performance
- **Fuse stages**: by default, stages are fused into a single actor for efficiency; use `.async` to introduce async boundaries when needed.
- **Batching**: use `grouped`, `batch`, or `batchWeighted` to process multiple elements together.
- **Parallelism**: use `mapAsync` or `mapAsyncUnordered` for concurrent processing; specify parallelism level.

### Error Handling
- **Supervision**: use `ActorAttributes.supervisionStrategy` to control error handling (resume, restart, stop).
- **Recovery**: use `recover`, `recoverWithRetries`, or `RestartSource`/`RestartFlow` for retryable failures.
- **Explicit error channels**: consider modeling errors as domain types in the stream rather than exceptions.

## Testing Stream Components

Use `akka-stream-testkit` for deterministic, in-memory testing without external dependencies.

### Core testing tools
- **TestSource.probe[T]**: manually control element emission and demand.
- **TestSink.probe[T]**: assert on received elements and verify backpressure.
- **TestProbe**: for integration with Akka actors.

### Testing patterns
1. **Isolated component tests**: test `Flow` instances independently.
2. **Backpressure verification**: ensure components respect downstream demand.
3. **Error handling**: verify supervision strategies and recovery behavior.
4. **Cancellation**: test cleanup on stream cancellation.

### Example: Testing a Flow
```scala
import akka.stream.scaladsl.{Flow, Keep, Source, Sink}
import akka.stream.testkit.scaladsl.{TestSource, TestSink}
import akka.actor.ActorSystem
import org.scalatest.matchers.should.Matchers
import org.scalatest.wordspec.AnyWordSpec

class FlowSpec extends AnyWordSpec with Matchers {
  implicit val system: ActorSystem = ActorSystem("test")

  "A simple Flow" should {
    "transform elements correctly" in {
      val doubleFlow = Flow[Int].map(_ * 2)

      val (pub, sub) = TestSource.probe[Int]
        .via(doubleFlow)
        .toMat(TestSink.probe[Int])(Keep.both)
        .run()

      sub.request(2)
      pub.sendNext(1)
      pub.sendNext(2)

      sub.expectNext(2)
      sub.expectNext(4)

      pub.sendComplete()
      sub.expectComplete()
    }

    "handle backpressure" in {
      val flow = Flow[Int].map(_ * 2)

      val (pub, sub) = TestSource.probe[Int]
        .via(flow)
        .toMat(TestSink.probe[Int])(Keep.both)
        .run()

      // Don't request yet
      pub.sendNext(1)
      
      // No elements should be received without demand
      sub.expectNoMessage()

      // Now request
      sub.request(1)
      sub.expectNext(2)

      pub.sendComplete()
      sub.expectComplete()
    }

    "propagate errors" in {
      val failingFlow = Flow[Int].map { n =>
        if (n == 0) throw new IllegalArgumentException("zero")
        else n * 2
      }

      val (pub, sub) = TestSource.probe[Int]
        .via(failingFlow)
        .toMat(TestSink.probe[Int])(Keep.both)
        .run()

      sub.request(2)
      pub.sendNext(1)
      sub.expectNext(2)

      pub.sendNext(0)
      sub.expectError() should be (an[IllegalArgumentException])
    }
  }
}
```

### Example: Testing a Source
```scala
"A custom Source" should {
  "emit expected elements" in {
    val source = Source(1 to 5).map(_ * 2)

    val sub = source.runWith(TestSink.probe[Int])

    sub.request(5)
    sub.expectNext(2, 4, 6, 8, 10)
    sub.expectComplete()
  }

  "respect backpressure" in {
    val source = Source(1 to 100)

    val sub = source.runWith(TestSink.probe[Int])

    // Request only 3 elements
    sub.request(3)
    sub.expectNext(1, 2, 3)

    // Source should not push more without demand
    sub.expectNoMessage()

    sub.request(2)
    sub.expectNext(4, 5)
  }
}
```

### Example: Testing a Sink
```scala
"A custom Sink" should {
  "consume all elements" in {
    val collected = scala.collection.mutable.ListBuffer[Int]()
    val sink = Sink.foreach[Int](collected += _)

    val pub = TestSource.probe[Int]
      .toMat(sink)(Keep.left)
      .run()

    pub.sendNext(1)
    pub.sendNext(2)
    pub.sendNext(3)
    pub.sendComplete()

    eventually {
      collected.toList shouldBe List(1, 2, 3)
    }
  }
}
```

## Common Patterns

### Simple transformation pipeline
```scala
import akka.stream.scaladsl.{Source, Sink}
import akka.actor.ActorSystem
import scala.concurrent.Future

implicit val system: ActorSystem = ActorSystem()
import system.dispatcher

val result: Future[Seq[Int]] = Source(1 to 10)
  .filter(_ % 2 == 0)
  .map(_ * 2)
  .runWith(Sink.seq)

result.foreach(println) // List(4, 8, 12, 16, 20)
```

### Async processing with mapAsync
```scala
import scala.concurrent.Future

def fetchUser(id: Int): Future[String] = Future.successful(s"User$id")

val userFlow = Flow[Int]
  .mapAsync(parallelism = 4)(id => fetchUser(id))

Source(1 to 100)
  .via(userFlow)
  .runWith(Sink.foreach(println))
```

### Reusable Flow components
```scala
// Define reusable Flows
val parseJson: Flow[String, JsValue, NotUsed] =
  Flow[String].map(Json.parse)

val validateUser: Flow[JsValue, User, NotUsed] =
  Flow[JsValue].map(_.as[User])

val saveToDb: Sink[User, Future[Done]] =
  Sink.foreachAsync(parallelism = 4)(user => db.save(user))

// Compose them
Source(jsonLines)
  .via(parseJson)
  .via(validateUser)
  .runWith(saveToDb)
```

### Fan-out / Fan-in with GraphDSL
```scala
import akka.stream.scaladsl.{GraphDSL, RunnableGraph, Broadcast, Merge}
import akka.stream.ClosedShape

val graph = RunnableGraph.fromGraph(GraphDSL.create() { implicit builder =>
  import GraphDSL.Implicits._

  val in = Source(1 to 10)
  val out = Sink.foreach[Int](println)

  val bcast = builder.add(Broadcast[Int](2))
  val merge = builder.add(Merge[Int](2))

  val evens = Flow[Int].filter(_ % 2 == 0).map(_ * 10)
  val odds = Flow[Int].filter(_ % 2 == 1).map(_ * 100)

  in ~> bcast ~> evens ~> merge ~> out
        bcast ~> odds  ~> merge

  ClosedShape
})

graph.run()
```

## Error Handling

### Supervision strategies
```scala
import akka.stream.{ActorAttributes, Supervision}

val decider: Supervision.Decider = {
  case _: IllegalArgumentException => Supervision.Resume
  case _: Exception => Supervision.Stop
}

Source(1 to 10)
  .map { n =>
    if (n == 5) throw new IllegalArgumentException("skip 5")
    n * 2
  }
  .withAttributes(ActorAttributes.supervisionStrategy(decider))
  .runWith(Sink.foreach(println))
// Prints: 2, 4, 6, 8, 12, 14, 16, 18, 20 (skips 5)
```

### Recover from failures
```scala
Source(1 to 5)
  .map { n =>
    if (n == 3) throw new RuntimeException("error at 3")
    n * 2
  }
  .recover {
    case _: RuntimeException => -1
  }
  .runWith(Sink.seq)
// Result: List(2, 4, -1)
```

### Retry with RestartSource
```scala
import akka.stream.scaladsl.RestartSource
import scala.concurrent.duration._

val restartSettings = RestartSettings.create(
  minBackoff = 1.second,
  maxBackoff = 10.seconds,
  randomFactor = 0.2
).withMaxRestarts(5, 1.minute)

val source = RestartSource.withBackoff(restartSettings) { () =>
  Source
    .future(fetchData())
    .mapMaterializedValue(_ => NotUsed)
}

source.runWith(Sink.foreach(println))
```

## Backpressure and Rate Control

### Throttle
```scala
import scala.concurrent.duration._

Source(1 to 1000)
  .throttle(10, 1.second) // 10 elements per second
  .runWith(Sink.foreach(println))
```

### Buffer with overflow strategy
```scala
import akka.stream.OverflowStrategy

Source(1 to 1000)
  .buffer(100, OverflowStrategy.dropHead)
  .runWith(Sink.foreach(println))
```

### Batching
```scala
Source(1 to 100)
  .grouped(10) // Group into batches of 10
  .runWith(Sink.foreach(batch => println(s"Batch: $batch")))
```

## Working Examples

### Example 1: File processing with backpressure
```scala
import akka.stream.scaladsl.{FileIO, Framing}
import akka.util.ByteString
import java.nio.file.Paths

val result = FileIO.fromPath(Paths.get("input.txt"))
  .via(Framing.delimiter(ByteString("\n"), maximumFrameLength = 1024))
  .map(_.utf8String)
  .filter(_.nonEmpty)
  .map(_.toUpperCase)
  .runWith(Sink.seq)
```

### Example 2: HTTP client with rate limiting
```scala
import akka.http.scaladsl.Http
import akka.http.scaladsl.model.{HttpRequest, HttpResponse}
import scala.concurrent.Future

val http = Http()

val requestFlow: Flow[String, String, NotUsed] = Flow[String]
  .throttle(10, 1.second) // Rate limit: 10 requests/second
  .mapAsync(parallelism = 4) { url =>
    http.singleRequest(HttpRequest(uri = url))
      .flatMap(_.entity.toStrict(5.seconds))
      .map(_.data.utf8String)
  }

Source(urls)
  .via(requestFlow)
  .runWith(Sink.foreach(println))
```

### Example 3: Database write with batching
```scala
val dbWriteSink: Sink[Record, Future[Done]] = Flow[Record]
  .grouped(100) // Batch 100 records
  .mapAsync(parallelism = 1) { batch =>
    database.batchInsert(batch)
  }
  .toMat(Sink.ignore)(Keep.right)

Source(records)
  .via(parseFlow)
  .via(validateFlow)
  .runWith(dbWriteSink)
```

### Example 4: Testing with TestKit (complete scenario)
```scala
import akka.stream.scaladsl.{Flow, Keep}
import akka.stream.testkit.scaladsl.{TestSource, TestSink}

class ThrottledFlowSpec extends AnyWordSpec with Matchers {
  implicit val system: ActorSystem = ActorSystem("test")

  "A throttled flow" should {
    "process elements at the specified rate" in {
      val throttledFlow = Flow[Int]
        .throttle(1, 100.millis)

      val (pub, sub) = TestSource.probe[Int]
        .via(throttledFlow)
        .toMat(TestSink.probe[Int])(Keep.both)
        .run()

      sub.request(3)
      
      pub.sendNext(1)
      pub.sendNext(2)
      pub.sendNext(3)

      // First element should arrive immediately
      sub.expectNext(1)

      // Remaining elements throttled
      sub.expectNoMessage(50.millis)
      sub.expectNext(2)
      sub.expectNoMessage(50.millis)
      sub.expectNext(3)

      pub.sendComplete()
      sub.expectComplete()
    }
  }
}
```

## Sources

Official documentation:
- **Akka Streams Design**: https://doc.akka.io/libraries/akka-core/current/general/stream/stream-design.html
- **Flows and Basics**: https://doc.akka.io/libraries/akka-core/current/stream/stream-flows-and-basics.html
- **Stream Graphs**: https://doc.akka.io/libraries/akka-core/current/stream/stream-graphs.html
- **Stream Composition**: https://doc.akka.io/libraries/akka-core/current/stream/stream-composition.html
- **Rate Control**: https://doc.akka.io/libraries/akka-core/current/stream/stream-rate.html
- **Stream Context**: https://doc.akka.io/libraries/akka-core/current/stream/stream-context.html
- **Reactive Streams Interop**: https://doc.akka.io/libraries/akka-core/current/stream/reactive-streams-interop.html
- **Error Handling**: https://doc.akka.io/libraries/akka-core/current/stream/stream-error.html
- **Stream TestKit**: https://doc.akka.io/libraries/akka-core/current/stream/stream-testkit.html
- **Stream Cookbook**: https://doc.akka.io/libraries/akka-core/current/stream/stream-cookbook.html
- **Pekko Streams**: https://pekko.apache.org/docs/pekko/current/stream/
