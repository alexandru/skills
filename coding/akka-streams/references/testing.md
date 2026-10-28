# Akka Streams: Testing Patterns and Examples

Sources:
- https://doc.akka.io/libraries/akka-core/current/stream/stream-testkit.html
- https://doc.akka.io/libraries/akka-core/current/stream/stream-cookbook.html

## Table of Contents

- [Dependency](#dependency)
- [Testing Philosophy](#testing-philosophy)
- [Basic Testing with Built-in Sources/Sinks](#basic-testing-with-built-in-sourcessinks)
- [TestSource and TestSink](#testsource-and-testsink)
- [Testing with TestProbe (Actor Integration)](#testing-with-testprobe-actor-integration)
- [Testing Error Handling](#testing-error-handling)
- [Testing Backpressure Scenarios](#testing-backpressure-scenarios)
- [Testing Async Operations](#testing-async-operations)
- [Testing Time-Based Operations](#testing-time-based-operations)
- [Testing Graph DSL](#testing-graph-dsl)
- [Testing Materialized Values](#testing-materialized-values)
- [Integration Testing](#integration-testing)
- [Common Testing Patterns](#common-testing-patterns)
- [Pekko Streams Testing](#pekko-streams-testing)

## Dependency

Add to your test scope:

**sbt**:
```scala
libraryDependencies += "com.typesafe.akka" %% "akka-stream-testkit" % AkkaVersion % Test
```

**Maven**:
```xml
<dependency>
  <groupId>com.typesafe.akka</groupId>
  <artifactId>akka-stream-testkit_${scala.binary.version}</artifactId>
  <scope>test</scope>
</dependency>
```

**For Pekko**: Replace `akka` with `org.apache.pekko` and use Pekko version.

## Testing Philosophy

1. **Test components in isolation**: separate `Source`, `Flow`, `Sink`
2. **Use TestKit for control**: `TestSource`, `TestSink`, `TestProbe`
3. **Test backpressure explicitly**: verify behavior under demand control
4. **Test error scenarios**: failures, cancellation, supervision
5. **Avoid testing Akka internals**: focus on your business logic

## Basic Testing with Built-in Sources/Sinks

### Testing a Sink
```scala
import akka.stream.scaladsl._
import scala.concurrent.Await
import scala.concurrent.duration._

"custom sink" should "fold elements correctly" in {
  val sinkUnderTest = Flow[Int]
    .map(_ * 2)
    .toMat(Sink.fold(0)(_ + _))(Keep.right)

  val future = Source(1 to 4).runWith(sinkUnderTest)
  val result = Await.result(future, 3.seconds)
  
  assert(result == 20) // (2 + 4 + 6 + 8)
}
```

### Testing a Source
```scala
"custom source" should "produce expected elements" in {
  val sourceUnderTest = Source.repeat(1).map(_ * 2)

  val future = sourceUnderTest.take(10).runWith(Sink.seq)
  val result = Await.result(future, 3.seconds)
  
  assert(result == Seq.fill(10)(2))
}
```

### Testing a Flow
```scala
"custom flow" should "transform elements" in {
  val flowUnderTest = Flow[Int].takeWhile(_ < 5)

  val future = Source(1 to 10)
    .via(flowUnderTest)
    .runWith(Sink.fold(Seq.empty[Int])(_ :+ _))
    
  val result = Await.result(future, 3.seconds)
  
  assert(result == (1 to 4))
}
```

## TestSource and TestSink

### TestSink for precise control
```scala
import akka.stream.testkit.scaladsl.TestSink

"source" should "emit expected elements with backpressure" in {
  val source = Source(1 to 4)
  
  source
    .runWith(TestSink.probe[Int])
    .request(2)           // Request only 2 elements
    .expectNext(1, 2)     // Should receive first 2
    .expectNoMessage(100.millis)  // Should not receive more
    .request(1)           // Request 1 more
    .expectNext(3)        // Should receive next
    .request(1)
    .expectNext(4)
    .expectComplete()     // Source should complete
}
```

### TestSource for element injection
```scala
import akka.stream.testkit.scaladsl.TestSource

"sink" should "handle elements correctly" in {
  val sinkUnderTest = Flow[Int]
    .map(_ * 2)
    .toMat(Sink.seq)(Keep.right)

  val (source, future) = TestSource.probe[Int]
    .toMat(sinkUnderTest)(Keep.both)
    .run()

  source.sendNext(1)
  source.sendNext(2)
  source.sendNext(3)
  source.sendComplete()

  val result = Await.result(future, 3.seconds)
  assert(result == Seq(2, 4, 6))
}
```

### Testing both ends
```scala
"flow" should "handle backpressure correctly" in {
  val flowUnderTest = Flow[Int].map(_ * 2)

  val (source, sink) = TestSource.probe[Int]
    .via(flowUnderTest)
    .toMat(TestSink.probe[Int])(Keep.both)
    .run()

  // Sink requests elements
  sink.request(2)
  
  // Source sends elements
  source.sendNext(1)
  source.sendNext(2)
  
  // Verify output
  sink.expectNext(2, 4)
  
  // Verify backpressure (no more demand)
  source.sendNext(3)
  sink.expectNoMessage(100.millis)
  
  // Request more
  sink.request(1)
  sink.expectNext(6)
  
  source.sendComplete()
  sink.expectComplete()
}
```

## Testing with TestProbe (Actor Integration)

### Using TestProbe with Sink.actorRef
```scala
import akka.testkit.TestProbe

"source" should "send elements to actor" in {
  val sourceUnderTest = Source(1 to 3)
  val probe = TestProbe()

  sourceUnderTest
    .runWith(Sink.actorRef(
      probe.ref,
      onCompleteMessage = "done",
      onFailureMessage = _ => "failed"
    ))

  probe.expectMsg(1)
  probe.expectMsg(2)
  probe.expectMsg(3)
  probe.expectMsg("done")
}
```

### Using pipe pattern
```scala
import akka.pattern.pipe
import akka.testkit.TestProbe

"source" should "produce correct result" in {
  val sourceUnderTest = Source(1 to 4).grouped(2)
  val probe = TestProbe()

  sourceUnderTest
    .runWith(Sink.seq)
    .pipeTo(probe.ref)(system.dispatcher)

  probe.expectMsg(3.seconds, Seq(Seq(1, 2), Seq(3, 4)))
}
```

## Testing Error Handling

### Testing recover
```scala
"flow" should "recover from errors" in {
  val flowUnderTest = Flow[Int]
    .map { n =>
      if (n == 5) throw new RuntimeException("boom")
      else n
    }
    .recover {
      case _: RuntimeException => 0
    }

  val future = Source(1 to 10)
    .via(flowUnderTest)
    .runWith(Sink.seq)
    
  val result = Await.result(future, 3.seconds)
  
  // Elements 1-4, then 0 (recovered), then stream completes
  assert(result == Seq(1, 2, 3, 4, 0))
}
```

### Testing with TestSink.probe
```scala
"flow" should "propagate errors" in {
  val flowUnderTest = Flow[Int].map { n =>
    if (n == 3) throw new RuntimeException("boom")
    else n * 2
  }

  Source(1 to 5)
    .via(flowUnderTest)
    .runWith(TestSink.probe[Int])
    .request(5)
    .expectNext(2, 4)
    .expectError() match {
      case e: RuntimeException => 
        assert(e.getMessage == "boom")
      case other => 
        fail(s"Expected RuntimeException, got $other")
    }
}
```

### Testing supervision strategies
```scala
import akka.stream.Supervision._

"flow" should "resume on errors with supervision" in {
  val decider: Decider = {
    case _: ArithmeticException => Resume
    case _ => Stop
  }

  val flowUnderTest = Flow[Int]
    .map(n => 10 / n) // Throws on 0
    .withAttributes(supervisionStrategy(decider))

  val future = Source(List(2, 1, 0, 1, 2))
    .via(flowUnderTest)
    .runWith(Sink.seq)
    
  val result = Await.result(future, 3.seconds)
  
  // 0 is skipped due to Resume
  assert(result == Seq(5, 10, 10, 5))
}
```

## Testing Backpressure Scenarios

### Slow consumer
```scala
"flow" should "handle slow consumer" in {
  val (source, sink) = TestSource.probe[Int]
    .via(Flow[Int].buffer(2, OverflowStrategy.backpressure))
    .toMat(TestSink.probe[Int])(Keep.both)
    .run()

  // Send more elements than buffer + demand
  source.sendNext(1)
  source.sendNext(2)
  source.sendNext(3)
  
  // Verify no elements received yet (no demand)
  sink.expectNoMessage(100.millis)
  
  // Now request and verify order preserved
  sink.request(3)
  sink.expectNext(1, 2, 3)
  
  source.sendComplete()
  sink.expectComplete()
}
```

### Fast producer, slow consumer
```scala
"flow" should "drop elements with dropHead strategy" in {
  val (source, sink) = TestSource.probe[Int]
    .via(Flow[Int].buffer(2, OverflowStrategy.dropHead))
    .toMat(TestSink.probe[Int])(Keep.both)
    .run()

  // Fill buffer and overflow
  source.sendNext(1)
  source.sendNext(2)
  source.sendNext(3)  // Drops 1
  source.sendNext(4)  // Drops 2
  source.sendNext(5)  // Drops 3
  
  sink.request(2)
  sink.expectNext(4, 5)  // Only newest elements
  
  source.sendComplete()
  sink.expectComplete()
}
```

## Testing Async Operations

### MapAsync behavior
```scala
import scala.concurrent.Future

"flow" should "handle async transformations" in {
  val flowUnderTest = Flow[Int].mapAsync(4) { n =>
    Future.successful(n * 2)
  }

  val future = Source(1 to 5)
    .via(flowUnderTest)
    .runWith(Sink.seq)
    
  val result = Await.result(future, 3.seconds)
  
  assert(result == Seq(2, 4, 6, 8, 10))
}
```

### Testing concurrency limits
```scala
// Test class setup required for this example:
// class ConcurrencySpec extends AnyFlatSpec with Matchers with Eventually

import org.scalatest.concurrent.Eventually
import org.scalatest.time.{Millis, Seconds, Span}

"flow" should "respect parallelism limit" in {
  import java.util.concurrent.atomic.AtomicInteger
  import scala.concurrent.Promise
  
  val concurrent = new AtomicInteger(0)
  val maxSeen = new AtomicInteger(0)
  val latch = Promise[Unit]()

  val flowUnderTest = Flow[Int].mapAsync(2) { n =>
    Future {
      val current = concurrent.incrementAndGet()
      maxSeen.updateAndGet(max => math.max(max, current))
      // Await.result here is acceptable only in tests for coordinating
      // concurrent execution; never use in production code
      Await.result(latch.future, 1.second)
      concurrent.decrementAndGet()
      n * 2
    }(system.dispatcher)
  }

  val future = Source(1 to 10)
    .via(flowUnderTest)
    .runWith(Sink.seq)
  
  // Use ScalaTest's eventually (from Eventually trait) to poll
  // until parallelism limit is reached
  implicit val defaultPatienceConfig: PatienceConfig = PatienceConfig(
    timeout = Span(3, Seconds),
    interval = Span(50, Millis)
  )
  
  // shouldBe requires Matchers trait mixed in
  eventually {
    maxSeen.get() shouldBe 2
  }
  
  // Release latch to complete processing
  latch.success(())
  // Await.result acceptable here for test synchronization only
  Await.result(future, 3.seconds)
  
  // Verify parallelism never exceeded limit
  assert(maxSeen.get() == 2)
}
```

## Testing Time-Based Operations

### Throttle
```scala
import akka.stream.testkit.TestSubscriber

"flow" should "throttle elements" in {
  val source = Source(1 to 5)
    .throttle(2, 1.second)

  val probe = source
    .runWith(TestSink.probe[Int])

  probe.request(5)
  
  // First 2 elements arrive immediately
  probe.expectNext(1, 2)
  
  // Next element takes ~500ms
  probe.expectNoMessage(400.millis)
  probe.expectNext(500.millis, 3)
  
  probe.cancel()
}
```

### GroupedWithin
```scala
"flow" should "batch by size and time" in {
  val (source, sink) = TestSource.probe[Int]
    .groupedWithin(5, 1.second)
    .toMat(TestSink.probe[Seq[Int]])(Keep.both)
    .run()

  sink.request(2)
  
  // Send 3 elements (less than batch size)
  source.sendNext(1)
  source.sendNext(2)
  source.sendNext(3)
  
  // Timeout triggers batch
  sink.expectNext(2.seconds, Seq(1, 2, 3))
  
  // Send 5 elements (meets batch size)
  (1 to 5).foreach(source.sendNext)
  
  // Batch emitted immediately
  sink.expectNext(100.millis, Seq(1, 2, 3, 4, 5))
  
  source.sendComplete()
  sink.expectComplete()
}
```

## Testing Graph DSL

### Testing complex graphs
```scala
import akka.stream.{ClosedShape, UniformFanInShape}
import akka.stream.scaladsl.GraphDSL

"graph" should "merge streams correctly" in {
  val graph = RunnableGraph.fromGraph(
    GraphDSL.create(TestSink.probe[Int]) { implicit builder => sink =>
      import GraphDSL.Implicits._
      
      val source1 = Source(1 to 3)
      val source2 = Source(10 to 12)
      val merge = builder.add(Merge[Int](2))
      
      source1 ~> merge
      source2 ~> merge
      merge ~> sink
      
      ClosedShape
    }
  )
  
  val probe = graph.run()
  
  probe.request(6)
  
  // Order not guaranteed with Merge
  val results = (1 to 6).map(_ => probe.expectNext()).toSet
  
  assert(results == Set(1, 2, 3, 10, 11, 12))
  probe.expectComplete()
}
```

## Testing Materialized Values

### Testing KillSwitch
```scala
import akka.stream.KillSwitches

"stream" should "support killswitch termination" in {
  val (killSwitch, probe) = Source.repeat(1)
    .viaMat(KillSwitches.single)(Keep.right)
    .toMat(TestSink.probe[Int])(Keep.both)
    .run()

  probe.request(3)
  probe.expectNext(1, 1, 1)
  
  // Terminate via killswitch
  killSwitch.shutdown()
  
  probe.expectComplete()
}
```

### Testing ActorRef source
```scala
import akka.stream.OverflowStrategy

"actorRef source" should "receive messages" in {
  val (actorRef, probe) = Source
    .actorRef[String](
      bufferSize = 10,
      OverflowStrategy.dropHead
    )
    .toMat(TestSink.probe[String])(Keep.both)
    .run()

  probe.request(3)
  
  actorRef ! "hello"
  actorRef ! "world"
  actorRef ! "!"
  
  probe.expectNext("hello", "world", "!")
  
  actorRef ! akka.actor.Status.Success("done")
  probe.expectComplete()
}
```

## Integration Testing

### Full stream integration
```scala
"complete pipeline" should "process end-to-end" in {
  val validation = Flow[String]
    .map(_.trim)
    .filter(_.nonEmpty)
    
  val transformation = Flow[String]
    .map(_.toUpperCase)
    
  val aggregation = Sink.fold(Seq.empty[String])(_ :+ _)

  val future = Source(List("  hello  ", "", "  world  "))
    .via(validation)
    .via(transformation)
    .runWith(aggregation)
    
  val result = Await.result(future, 3.seconds)
  
  assert(result == Seq("HELLO", "WORLD"))
}
```

## Common Testing Patterns

### Setup and teardown
```scala
import akka.actor.ActorSystem
import akka.stream.Materializer
import org.scalatest.{BeforeAndAfterAll, Suite}

trait StreamSpec extends BeforeAndAfterAll { this: Suite =>
  implicit val system: ActorSystem = ActorSystem("test")
  implicit val mat: Materializer = Materializer(system)
  
  override protected def afterAll(): Unit = {
    system.terminate()
    super.afterAll()
  }
}
```

### Testing with ScalaTest async
```scala
import org.scalatest.concurrent.ScalaFutures
import org.scalatest.flatspec.AsyncFlatSpec

class AsyncStreamSpec extends AsyncFlatSpec with ScalaFutures {
  "source" should "complete successfully" in {
    val future = Source(1 to 10)
      .runWith(Sink.fold(0)(_ + _))
      
    future.map { result =>
      assert(result == 55)
    }
  }
}
```

## Pekko Streams Testing

For Pekko Streams, replace imports:

```scala
// Akka
import akka.stream.scaladsl._
import akka.stream.testkit.scaladsl._

// Pekko
import org.apache.pekko.stream.scaladsl._
import org.apache.pekko.stream.testkit.scaladsl._
```

All testing patterns remain identical.
