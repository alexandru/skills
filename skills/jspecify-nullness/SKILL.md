---
name: jspecify-nullness
description: JSpecify nullness annotations for Java APIs and tooling. Use when adopting or migrating JSpecify annotations, designing null-safe Java signatures, fixing generic bounds and type-use placement, or interpreting Kotlin interop, annotation-processor, and tool-conformance behavior.
---

# JSpecify Nullness (Java)

## Quick start
- Add `org.jspecify:jspecify:1.0.0` as a visible API dependency for Java libraries.
- Prefer `@NullMarked` at package or class scope; add `@Nullable` only where `null` is allowed.
- Treat unannotated types outside `@NullMarked` as unspecified nullness, not non-null.
- Decide generic bounds deliberately: `<T extends @Nullable Object>` accepts nullable type arguments; `<T>` does not in a null-marked scope.
- Keep `@Nullable`/`@NonNull` in JSpecify-recognized type-use locations, especially for arrays, nested types, type arguments, and bounds.
- Read `references/jspecify-nullness.md` before substantial annotation, migration, or tooling advice.

## Workflow
1. Confirm consumer constraints: nullness checker, Kotlin compiler behavior, and annotation processors.
2. Add the JSpecify dependency without hiding it from downstream users.
3. Annotate nullable types first, then add `@NullMarked` at class or package scope.
4. Fix generics: choose nullable/non-null bounds and annotate type-variable uses only when the use differs from the type argument.
5. Compile examples for syntax, then run a JSpecify-aware nullness analyzer and fix findings before expanding scope.

## Rules of thumb
- Do not annotate local-variable root types or casts; annotate only nested type arguments/components there.
- For fields, parameters, and returns, `@Nullable String[]` means nullable elements; `String @Nullable []` means the array reference is nullable.
- For nested types, annotate the nested type as `Map.@Nullable Entry`, not the outer type.
- Use `@NonNull T` only to force a type-variable use non-null when the type argument may be nullable.
- Use `@NullUnmarked` only as an incremental escape hatch inside a null-marked scope.

## Output expectations
- Provide annotated signatures and call-site implications.
- Explain generic bound choices and type-use placement.
- Call out tool-conformance limits instead of promising specific diagnostics.
- For skill edits, run `jbang skills/jspecify-nullness/scripts/verify-examples.java`.

## References
- Load `references/jspecify-nullness.md` for source-backed guidance, examples, and representative prompts.
