---
name: simplicity
description: Teaches the simplification lenses of constraints, simplicity, and parametricity. Use when simplifying or refactoring code, or reviewing simplification opportunities.
---

## Lenses

The following lenses guide the pursuit of simplicity.

### Constraints (Bjarnason, "Constraints Liberate, Liberties Constrain")

What freedom can we remove so fewer incorrect implementations are possible?

The more a piece of code can do, the less a reader can predict what it will do. Freedom at one level becomes constraint at the next. A function allowed to return an empty list forces every caller to handle one; a function allowed to mutate shared state forces every reader to track it. Pick the least powerful type, signature or abstraction that still does the job, and put the constraint where the value is created, so the checks it replaces disappear downstream.

A change removes complexity here when a state or implementation that used to compile no longer does, and the check that guarded against it goes away. Hunt invalid states the types allow, invariants held up by runtime checks or convention (taking the first element after an emptiness guard, flags that must agree with other fields), types wider than the values they carry, functions handed more capability than they use, and defensive branches nothing can reach. A reachable invalid state is often a bug; report it as one.

### Simplicity (Hickey, "Simple Made Easy")

Which independent concerns have become entangled? Can they be understood separately?

Simple means one fold, not braided with anything else. It is objective, and it is a different axis from easy, which only means familiar or close at hand. Two concerns are complected when a reader can't think about one without the other. Separate files don't fix that on their own, because modules can still be braided through shared state, flags or conventions. Judge the running artifact, not how pleasant the code was to write.

A change removes complexity here when a question about one concern no longer needs the other concern's code to answer it. Hunt one concept defined twice, caches and side maps kept apart from the data they describe, fast paths woven into logic, stored fields that could be derived, state threaded through code that only needs a value, and conditionals that encode a decision made elsewhere.

### Parametricity (Wadler, "Theorems for free!")

What does the type actually guarantee, and what still depends on implementation discipline?

Read a type as a theorem. A function from a list of `A` to a list of `A`, for any `A`, can only drop, repeat or reorder elements, because it has no operations on `A`. So mapping a function over the input before or after calling it gives the same result, for every such function. The more general and precise the type, the more it proves. Concrete types like strings, integers and booleans prove almost nothing, and escape hatches like `null`, casts, runtime type tests, reflection, exceptions and side effects weaken whatever the type did prove. Any property they carry rests on discipline.

A change removes complexity here when a property that held by discipline now holds by signature, and the comment, convention or caller check that kept it true goes away. Hunt unnamed tuples whose order matters, strings standing in for closed sets, cached results that depend on arguments missing from the cache key, functions that take a concrete type they never inspect, and invariants a signature could enforce that only a comment states.
