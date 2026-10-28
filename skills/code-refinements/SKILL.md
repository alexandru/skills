---
name: code-refinements
description: Defines what refined code looks like through the three lenses of constraints, simplicity, and parametricity, with rules for type proofs, no partial calls, explicit signatures, unrepresentable wrong states, hot-path discipline, and style. Use when writing, changing, or reviewing code to a refinement bar, or whenever the user asks for code to follow the rules in code-refinements.
---

# Code Refinements

Refined code does the same job with less design: fewer states that can be wrong, fewer concerns braided together, fewer properties resting on discipline. What it does without is nameable — a runtime check, a branch, a partial call, a parameter, a stored field, a duplicate definition, a dependency between two components, a convention the reader had to remember — and every type or abstraction it carries earns its keep by the checks and conventions it makes unnecessary. Line count is not the measure: fewer lines often accompany refinement, but code shrunk to fit a count is not refined.

The deepest refinement is in the model, not in the tidiness: a core data model in which the invalid states cannot be written, one pass where a lesser design needs two, no module beyond what the job needs, a contract carried by signatures, with no checks needed on either side. Edge cases belong to the model, not to the branches: a check, a table entry or a branch per case is complexity, not refinement.

## Lenses

Each lens asks one question and names a different kind of complexity.

### Constraints (Bjarnason, "Constraints Liberate, Liberties Constrain")

What freedom can we remove so fewer incorrect implementations are possible?

The more a piece of code can do, the less a reader can predict what it will do. Freedom at one level becomes constraint at the next. A function allowed to return an empty list forces every caller to handle one; a function allowed to mutate shared state forces every reader to track it. Pick the least powerful type, signature or abstraction that still does the job, and put the constraint where the value is created, so the checks it replaces disappear downstream.

In refined code, invalid states do not compile, so no check guards against them. Unrefined code shows invalid states the types allow, invariants held up by runtime checks or convention (a first element taken after an emptiness guard, flags that must agree with other fields), types wider than the values they carry, functions handed more capability than they use, and defensive branches nothing can reach. A reachable invalid state is a bug.

### Simplicity (Hickey, "Simple Made Easy")

Which independent concerns have become entangled? Can they be understood separately?

Simple means one fold, not braided with anything else. It is objective, and it is a different axis from easy, which only means familiar or close at hand. Two concerns are complected when a reader can't think about one without the other. Separate files don't fix that on their own, because modules can still be braided through shared state, flags or conventions. Judge the running artifact, not how pleasant the code was to write.

In refined code, a question about one concern is answered without any other concern's code. Unrefined code defines one concept twice, keeps caches and side maps apart from the data they describe, weaves fast paths into logic, stores fields that could be derived, threads state through code that only needs a value, and encodes in conditionals decisions made elsewhere.

### Parametricity (Wadler, "Theorems for free!")

What does the type actually guarantee, and what still depends on implementation discipline?

Read a type as a theorem. A function from a list of `A` to a list of `A`, for any `A`, can only drop, repeat or reorder elements, because it has no operations on `A`. So mapping a function over the input before or after calling it gives the same result, for every such function. The more general and precise the type, the more it proves. Concrete types like strings, integers and booleans prove almost nothing, and escape hatches like `null`, casts, runtime type tests, reflection, exceptions and side effects weaken whatever the type did prove. Any property they carry rests on discipline.

In refined code, properties hold by signature, not by comment, convention or caller check. Unrefined code leans on unnamed tuples whose order matters, strings standing in for closed sets, cached results that depend on arguments missing from the cache key, functions that take a concrete type they never inspect, and invariants a signature could enforce that only a comment states.

## Rules

The lenses name the complexity; these rules state what code free of it looks like.

### No partial calls

Refined code holds no partial call, an operation that fails on some input its type allows: the first element of a list that may be empty, a map or dictionary lookup that throws on a missing key, an unchecked unwrap of an optional value (`Option.get`, `unwrap()`, a `!` non-null assertion), a cast, or a match or switch that misses a case. The type carries the proof: a non-empty type from where the list is built, the looked-up value in place of its key, a match that covers every case. An optional value is a type, not a sentinel default that code must remember to check. A hot path is the one exception, only when an established invariant makes the call safe and performance evidence shows the safe form adds meaningful cost.

### Explicit signatures

Every top-level function declares its parameter and return types; every field declares its type. In languages with optional type annotations, keep these contracts explicit.

Prefer type inference for local values and nested helpers when the inferred types preserve the intended constraints. Add explicit annotations where inference is unavailable, loses constraints, or permits unintended widening.

Required annotations state the contract to readers and the compiler. Inside implementations, annotate only to enforce a constraint or clarify an otherwise unclear type.

### Wrong states are unrepresentable

A bug shows where the design lets a wrong state through; refined code admits no such state. Parse, don't validate: turn less-structured input into a representation that preserves the proof of its invariants, not a check whose result is discarded. Wrong input cannot be represented, or it flows through the mechanism that already handles its kind — one cause, one mechanism. A downstream runtime guard holding up an invariant, or an `if` carrying an edge case, marks a wrong state the design still admits.

### Hot paths stay fast

Code that runs per request, per entity, per item or per field does no more work per call than the job needs. The smells: an allocation the job never asked for, a scan doing a lookup's job, two passes doing one pass's work, a fast path missing where one belongs.

### Style

Code reads like its neighbors: the project's formatter, import style, naming and idioms. A comment belongs only where the code alone would mislead; a comment that restates a name says nothing. A doc comment states the contract the signature cannot, in the project's doc-comment conventions.

## Foundations

See [the philosophical foundations](references/philosophical-foundations.md) for original sources and how parsing preserves type proofs.
