---
name: akka-streams
description: Scala/Java Akka Streams and Pekko Streams reactive stream processing with best practices and testing guidance. Use for designing streaming pipelines, backpressure-aware data processing, testing stream components, or deciding when Streams are the right tool vs plain functions.
---

# Akka Streams / Pekko Streams

## Quick start
- Use Akka Streams (or Pekko Streams) for backpressure-aware processing of potentially unbounded data; avoid using Streams for operations that fit in plain functions or collections.
- Prefer small, composable stream components (`Flow`, `Source`, `Sink`) over monolithic graphs.
- Test stream components with `akka-stream-testkit` (`TestSource`, `TestSink`, `TestProbe`) for deterministic, in-memory validation.
- Read `references/akka-streams.md` for design principles, best practices, testing patterns, and working examples.

## Workflow
1. Assess whether Streams are the right tool: use for async I/O, backpressure, or unbounded data; avoid for in-memory transformations or small collections.
2. Design small, reusable stream components: `Source[T, Mat]`, `Flow[In, Out, Mat]`, `Sink[T, Mat]`.
3. Compose components with `via`, `to`, and graph DSL (`GraphDSL`) when needed.
4. Materialize streams with `run()` or `runWith()` to obtain materialized values.
5. Test components using `TestSource.probe`, `TestSink.probe`, and assertions on demand/supply.

## When NOT to use Streams
- **Plain data transformations**: use `map`, `filter`, `flatMap` on collections instead of wrapping in a `Source`.
- **Small, bounded data**: prefer standard library operations unless backpressure or async integration is required.
- **Simple async operations**: use `Future` directly for single async results; Streams add overhead for one-shot tasks.

## Testing rules
- Always test stream components in isolation using `akka-stream-testkit`.
- Use `TestSource.probe[T]` to control upstream demand and emission.
- Use `TestSink.probe[T]` to assert on downstream demand and received elements.
- Verify backpressure behavior: ensure components respect downstream demand and don't buffer excessively.

## Output expectations
- Design reusable stream components with clear input/output types.
- Document materialized value types and their semantics.
- Include error handling strategies (`Supervision`, `recover`, `recoverWithRetries`).
- Provide test cases for normal flow, error scenarios, and cancellation.

## References
- Load `references/akka-streams.md` for comprehensive guidance, examples, and testing patterns.
- For concrete samples and cookbook recipes, read `references/akka-streams.md`.
