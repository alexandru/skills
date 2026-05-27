---
name: kotlin-java-library
description: Helps agents design and review Kotlin library APIs for Java consumers. Use when building Kotlin code intended for Java callers, shaping JVM signatures with @JvmName, @JvmOverloads, @JvmStatic, @JvmField, @Throws, @JvmRecord, nullability, records, and backward/binary compatibility rules.
---

# Kotlin Java Library Design

## Quick start
- Read `references/kotlin-java-library.md` before changing public Kotlin APIs for Java consumers.
- Design Kotlin APIs as if the primary caller is Java: explicit overloads, stable names, and predictable nullability.
- Use JVM interop annotations (`@JvmOverloads`, `@JvmStatic`, `@JvmField`, `@JvmName`) to shape the Java surface.
- Prefer Java-friendly top-level functions with `@file:JvmName`, and use `@file:JvmMultifileClass` when splitting across files.
- Use `fun interface` for Java callbacks; avoid function types that return `Unit`.
- Document checked exceptions with `@Throws` and return defensive copies for read-only collections.
- Follow binary compatibility rules: add overloads or new members instead of changing published signatures.
- Validate examples with `scripts/verify-examples.java` when changing the reference or public API patterns.

## Workflow
1. Identify which public APIs must be Java-friendly (constructors, factories, utilities, callbacks, records).
2. Shape the Java surface with JVM annotations and explicit overloads.
3. Audit public signatures for Java stability (names, nullability, overload sets, and collection exposure).
4. Apply backward-compatibility rules before publishing; treat `@PublishedApi` members as public.
5. Validate with Java call-site examples.
6. Run `jbang skills/kotlin-java-library/scripts/verify-examples.java`; if it fails, fix the sample or document why it cannot be tested.

## Rules of thumb
- Avoid Kotlin-only surface features in public API: default args without overloads, extension-only entry points, and name clashes.
- Explicitly declare public return and property types.
- Use `@JvmOverloads` for Java-callable optional parameters, and provide explicit overloads when behavior differs.
- Use `@JvmStatic` for companion/object members meant to be static in Java.
- Use `const val` for compile-time constants and `@JvmField` only for immutable non-`const` fields you want exposed as fields.
- Use `@JvmName` to resolve signature clashes or to provide a stable Java name.
- Use `@JvmRecord` only for new Java-record value carriers targeting JVM 16+; do not retrofit it onto published classes.
- Avoid `Nothing` in public generic signatures; it becomes raw types in Java.

## Output expectations
- Offer Java-call-site examples when proposing API changes.
- Call out binary compatibility risks and safer alternatives.
- Include validation results for non-trivial snippets.

## References
- Load `references/kotlin-java-library.md` for interop details, examples, and testing prompts.
