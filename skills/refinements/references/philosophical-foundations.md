# Philosophical foundations

These sources motivate a model-first quality bar: eliminate checks and conventions by constraining representations and interfaces.

## Constraints

[Rúnar Bjarnason, "Constraints Liberate, Liberties Constrain"](https://www.youtube.com/watch?v=GqmsQeSzMdw) argues for restraint and precision over expressive power and flexibility: constraints on components provide freedom when composing systems. The question is what the component's interface prevents it from doing, and what callers therefore no longer need to account for.

## Simplicity

[Rich Hickey, "Simple Made Easy"](https://www.infoq.com/presentations/Simple-Made-Easy/) distinguishes simplicity from familiarity or convenience. Simplicity means independent concerns are not interleaved. Putting intertwined concerns in separate files does not disentangle them; changing the model so each can be understood independently does.

## Parametricity

[Philip Wadler, "Theorems for free!"](https://doi.org/10.1145/99370.99404) derives properties of polymorphic functions from their types. With no operations on an abstract type, implementations cannot inspect its values to decide what to do. The signature constrains implementations, making properties follow without reading their bodies.

The formal guarantees depend on the language and available operations: nontermination, casts, runtime type inspection and effects can weaken them. That is a reason to constrain those capabilities, not to replace type proofs with convention.

## Parse, don't validate

[Alexis King, "Parse, don't validate"](https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/) distinguishes checking a property from preserving evidence of that property in a more precise representation. A check returning `()` discards what it learned; a parser returning `NonEmpty a` retains proof that the list is non-empty, so consumers need no emptiness guard or partial first-element operation.

Parsing can reject input. The distinction is not whether a runtime check occurs, but whether its successful result makes the invariant part of the data and contract. Parse before acting on input, and have downstream functions require the representation they need. A smart constructor with a hidden constructor can preserve the same evidence when the property cannot be expressed directly in the type's structure.
