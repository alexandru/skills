# Akka Streams: Core Concepts and Operators

Sources:
- https://doc.akka.io/libraries/akka-core/current/stream/stream-flows-and-basics.html
- https://doc.akka.io/libraries/akka-core/current/stream/stream-graphs.html
- https://doc.akka.io/libraries/akka-core/current/stream/stream-composition.html
- https://doc.akka.io/libraries/akka-core/current/stream/stream-rate.html
- https://doc.akka.io/libraries/akka-core/current/stream/stream-error.html
- https://doc.akka.io/libraries/akka-core/current/stream/reactive-streams-interop.html

## Table of Contents

- [Core Abstractions](#core-abstractions)
- [Composition](#composition)
- [Materialization](#materialization)
- [Graph DSL](#graph-dsl)
- [Backpressure and Buffering](#backpressure-and-buffering)
- [Error Handling](#error-handling)
- [Reactive Streams Interop](#reactive-streams-interop)
- [Async Boundaries](#async-boundaries)
- [Context Propagation](#context-propagation)
- [Time-Based Operations](#time-based-operations)
- [Common Patterns](#common-patterns)

## Core Abstractions

### Source
An operator with exactly one output, emitting data elements:

```scala
import akka.stream.scaladsl._

// From collection
val source1 = Source(1 to 10)

// From iterator
val source2 = Source.fromIterator(() => Iterator.from(1))

// From Future
val source3 = Source.future(Future.successful(42))

// Single element
val source4 = Source.single("hello")

// Repeating element
val source5 = Source.repeat("tick")

// Tick source
val source6 = Source.tick(0.seconds, 1.second, "tick")
```

### Sink
An operator with exactly one input, consuming elements:

```scala
// Fold into result
val sink1 = Sink.fold[Int, Int](0)(_ + _)

// Collect to sequence
val sink2 = Sink.seq[String]

// Foreach side effect
val sink3 = Sink.foreach[Int](println)

// Ignore all elements
val sink4 = Sink.ignore

// Take first element
val sink5 = Sink.head[Int]

// Take last element  
val sink6 = Sink.last[Int]
```

### Flow
An operator with one input and one output:

```scala
// Map transformation
val flow1 = Flow[Int].map(_ * 2)

// Filter elements
val flow2 = Flow[Int].filter(_ > 0)

// Async transformation
val flow3 = Flow[String].mapAsync(4)(url => fetchAsync(url))

// Stateful operations
val flow4 = Flow[Int].scan(0)(_ + _)

// Grouped batching
val flow5 = Flow[Int].grouped(10)
```

### RunnableGraph
A fully connected graph ready to materialize:

```scala
val runnable: RunnableGraph[Future[Int]] = 
  Source(1 to 10)
    .toMat(Sink.fold(0)(_ + _))(Keep.right)

// Materialize and run
val result: Future[Int] = runnable.run()
```

## Composition

### Linear composition
```scala
// Source + Flow = Source
val composedSource: Source[String, NotUsed] = 
  Source(1 to 10).map(_.toString)

// Flow + Sink = Sink
val composedSink: Sink[Int, Future[Int]] = 
  Flow[Int].map(_ * 2).toMat(Sink.fold(0)(_ + _))(Keep.right)

// Source + Sink = RunnableGraph
val graph: RunnableGraph[NotUsed] = 
  Source(1 to 10).to(Sink.foreach(println))
```

### Via and to
```scala
val source = Source(1 to 10)
val flow = Flow[Int].map(_ * 2)
val sink = Sink.foreach[Int](println)

// Using via for Flow
source.via(flow).to(sink).run()

// Equivalent to:
source.map(_ * 2).to(sink).run()
```

## Materialization

Materialized values represent runtime artifacts:

```scala
import akka.stream.scaladsl._

// Keep left materialized value (Source's NotUsed)
val m1: NotUsed = Source(1 to 10)
  .toMat(Sink.ignore)(Keep.left)
  .run()

// Keep right materialized value (Sink's Future)
val m2: Future[Done] = Source(1 to 10)
  .toMat(Sink.ignore)(Keep.right)
  .run()

// Keep both as tuple
val m3: (NotUsed, Future[Done]) = Source(1 to 10)
  .toMat(Sink.ignore)(Keep.both)
  .run()

// Combine with custom function
val m4: Future[String] = Source(1 to 10)
  .toMat(Sink.ignore) { (_, done) => 
    done.map(_ => "completed")
  }
  .run()
```

### Common materialized values
```scala
// ActorRef for sending elements
val ref: ActorRef = Source
  .actorRef[String](bufferSize = 100, OverflowStrategy.dropHead)
  .to(Sink.foreach(println))
  .run()

ref ! "hello"

// KillSwitch for manual termination
val killSwitch: UniqueKillSwitch = Source
  .repeat("tick")
  .viaMat(KillSwitches.single)(Keep.right)
  .to(Sink.ignore)
  .run()

killSwitch.shutdown()
```

## Graph DSL

Complex topologies use `GraphDSL`:

```scala
import akka.stream.scaladsl.GraphDSL
import akka.stream.{ClosedShape, UniformFanInShape, UniformFanOutShape}

val graph = RunnableGraph.fromGraph(GraphDSL.create() { implicit builder =>
  import GraphDSL.Implicits._

  val source = Source(1 to 10)
  val broadcast = builder.add(Broadcast[Int](2))
  val merge = builder.add(Merge[Int](2))
  val sink = Sink.foreach[Int](println)

  source ~> broadcast ~> Flow[Int].map(_ * 2) ~> merge ~> sink
            broadcast ~> Flow[Int].map(_ * 3) ~> merge

  ClosedShape
})

graph.run()
```

### Common graph junctions

**Broadcast**: one input, N outputs (duplicates elements)
```scala
val bcast = Broadcast[Int](2)
```

**Merge**: N inputs, one output (picks from any input)
```scala
val merge = Merge[Int](2)
```

**Balance**: one input, N outputs (distributes elements)
```scala
val balance = Balance[Int](2)
```

**Zip**: two inputs, one output (pairs elements)
```scala
val zip = Zip[Int, String]()
```

**Concat**: two inputs, one output (first exhausts, then second)
```scala
val concat = Concat[Int]()
```

## Backpressure and Buffering

### Buffer strategies
```scala
// Backpressure downstream (wait for space)
source.buffer(100, OverflowStrategy.backpressure)

// Drop oldest on overflow
source.buffer(100, OverflowStrategy.dropHead)

// Drop newest on overflow
source.buffer(100, OverflowStrategy.dropTail)

// Drop entire buffer on overflow
source.buffer(100, OverflowStrategy.dropBuffer)

// Drop incoming element on overflow
source.buffer(100, OverflowStrategy.dropNew)

// Fail stream on overflow
source.buffer(100, OverflowStrategy.fail)
```

### Rate control
```scala
// Throttle to max rate
source.throttle(10, 1.second)

// Throttle with burst
source.throttle(10, 1.second, 100, ThrottleMode.Shaping)

// Debounce (emit only after silence period)
source.debounce(200.millis)

// Conflate (combine during backpressure)
source.conflate((acc, elem) => acc + elem)

// Batch with time window
source.groupedWithin(100, 1.second)
```

## Error Handling

### Recover
Emit a fallback value on error, then complete:

```scala
Source(1 to 10)
  .map(n => 100 / (n - 5)) // Throws on n=5
  .recover {
    case _: ArithmeticException => 0
  }
  .runWith(Sink.seq)
```

### RecoverWithRetries
Switch to alternate source on error:

```scala
val fallback = Source(List(-1, -2, -3))

Source(1 to 10)
  .map(risky)
  .recoverWithRetries(attempts = 3, {
    case _: Exception => fallback
  })
  .runWith(Sink.seq)
```

### Supervision
Control per-operator error behavior:

```scala
import akka.stream.Supervision._

val decider: Decider = {
  case _: IllegalArgumentException => Resume
  case _: RuntimeException => Restart
  case _ => Stop
}

Source(1 to 10)
  .map(risky)
  .withAttributes(supervisionStrategy(decider))
  .runWith(Sink.ignore)
```

## Reactive Streams Interop

Convert to/from Reactive Streams interfaces:

```scala
import org.reactivestreams.{Publisher, Subscriber}

// Source to Publisher
val publisher: Publisher[Int] = 
  Source(1 to 10).runWith(Sink.asPublisher(fanout = false))

// Publisher to Source
val source: Source[Int, NotUsed] = 
  Source.fromPublisher(publisher)

// Sink to Subscriber
val subscriber: Subscriber[Int] = 
  Flow[Int].map(_ * 2).to(Sink.ignore).runWith(Source.asSubscriber)

// Subscriber to Sink
val sink: Sink[Int, NotUsed] = 
  Sink.fromSubscriber(subscriber)
```

## Async Boundaries

Explicit async boundaries for parallelism:

```scala
// Default: operators fused, run on same actor
Source(1 to 10)
  .map(_ * 2)      // Fused
  .filter(_ > 5)   // Fused
  .runWith(Sink.seq)

// Explicit async boundaries
Source(1 to 10)
  .map(_ * 2)
  .async  // Forces async boundary here
  .filter(_ > 5)
  .async  // And here
  .runWith(Sink.seq)
```

## Context Propagation

Attach metadata to elements:

```scala
import akka.stream.scaladsl.SourceWithContext

// Source with context
SourceWithContext
  .fromTuples(Source(List((1, "a"), (2, "b"))))
  .map(_ * 2)  // Only transforms data, keeps context
  .runWith(Sink.seq)
  // Result: List((2, "a"), (4, "b"))
```

## Time-Based Operations

```scala
// Delay each element
source.delay(1.second)

// Initial delay only
source.initialDelay(5.seconds)

// Timeout if no elements
source.idleTimeout(10.seconds)

// Complete after timeout
source.completionTimeout(1.minute)

// Take elements within time
source.takeWithin(30.seconds)

// Drop elements within time
source.dropWithin(5.seconds)
```

## Common Patterns

### MapAsync vs MapAsyncUnordered
```scala
// Preserves order, waits for slow elements
source.mapAsync(parallelism = 4)(slowOp)

// Emits as soon as any future completes
source.mapAsyncUnordered(parallelism = 4)(slowOp)
```

### Stateful operations
```scala
// Scan (like fold but emits intermediate results)
Source(1 to 5).scan(0)(_ + _)
// Emits: 0, 1, 3, 6, 10, 15

// StatefulMapConcat for complex state
Source(1 to 10).statefulMapConcat { () =>
  var sum = 0
  elem => {
    sum += elem
    if (sum > 20) List(sum) else Nil
  }
}
```

### Collecting
```scala
// Collect with partial function
source.collect {
  case x if x > 0 => x * 2
}

// Equivalent to filter + map
source.filter(_ > 0).map(_ * 2)
```
