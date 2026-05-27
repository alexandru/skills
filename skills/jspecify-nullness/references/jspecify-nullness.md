# JSpecify Nullness - Reference

Source-backed guidance for applying JSpecify annotations in Java APIs. The Java snippets below are mirrored in `skills/jspecify-nullness/scripts/verify-examples.java`; run that script after changing the examples.

Sources:
- https://jspecify.dev/docs/start-here/
- https://jspecify.dev/docs/user-guide/
- https://jspecify.dev/docs/whether/
- https://jspecify.dev/docs/using/
- https://jspecify.dev/docs/applying/
- https://jspecify.dev/docs/spec/
- https://jspecify.dev/docs/tool-conformance/

## Table of Contents
- [Model](#model)
- [Dependency and visibility](#dependency-and-visibility)
- [Adoption workflow](#adoption-workflow)
- [Core API pattern](#core-api-pattern)
- [Null-marked scopes](#null-marked-scopes)
- [Recognized annotation locations](#recognized-annotation-locations)
- [Array and nested-type placement](#array-and-nested-type-placement)
- [Generics and type variables](#generics-and-type-variables)
- [Migration notes](#migration-notes)
- [Tooling and conformance](#tooling-and-conformance)
- [Kotlin and annotation processors](#kotlin-and-annotation-processors)
- [Checklist](#checklist)
- [Representative prompts](#representative-prompts)

## Model
- JSpecify defines annotation types in `org.jspecify.annotations` plus semantics for Java type usages.
- Nullness has four states: nullable, non-null, parametric for type variables, and unspecified.
- `@Nullable` means the annotated type usage includes `null`; `@NonNull` excludes `null`.
- `@NullMarked` makes otherwise unannotated type usages in the scope non-null, with documented exceptions.
- `@NullUnmarked` removes the effect of an enclosing `@NullMarked` scope for incremental migration.
- Unannotated code outside a null-marked scope remains unspecified; do not treat it as non-null.

## Dependency and visibility
- Use `org.jspecify:jspecify:1.0.0`.
- The annotations are in package `org.jspecify.annotations`; the Java module name is `org.jspecify`.
- Do not hide the dependency from downstream users. For Gradle Java libraries, prefer `api("org.jspecify:jspecify:1.0.0")`; for Maven, avoid `provided` and `optional`.
- The annotations have runtime retention, but they define type information rather than runtime null checks.

## Adoption workflow
1. Start with a small class or package that has few internal dependencies, and move from called code toward callers.
2. Mark obvious nullable type usages first: `return null`, explicit `parameter == null` handling, nullable fields, and calls that pass `null`.
3. Review generic declarations before adding `@NullMarked`; decide whether each type parameter permits nullable type arguments.
4. Add `@NullMarked` at package or class scope, using `@NullUnmarked` only for legacy pockets that are not ready.
5. Run nullness analysis on the annotated code, then on calling code, and fix either annotations or callers as findings appear.

## Core API pattern
Use `@NullMarked` to avoid repeating `@NonNull` in ordinary API signatures:

```java
@NullMarked
final class Strings {
  static @Nullable String emptyToNull(String value) {
    return value.isEmpty() ? null : value;
  }

  static String nullToEmpty(@Nullable String value) {
    return value == null ? "" : value;
  }
}
```

Call-site implication: `emptyToNull(null)` violates the contract, while callers of `emptyToNull` must handle a nullable result. `nullToEmpty(null)` is allowed and returns a non-null `String`.

## Null-marked scopes
- Recognized locations for `@NullMarked` and `@NullUnmarked`: named classes, packages, methods, and constructors. `@NullMarked` is also recognized on modules; `@NullUnmarked` is not.
- Package scopes are not hierarchical. Marking `com.example` does not mark `com.example.internal`.
- If the same declaration has both `@NullMarked` and `@NullUnmarked`, the spec treats it like neither is present.
- Use package-level `@NullMarked` for mature packages, class-level for smaller adoption, and method-level only for narrow boundaries.

## Recognized annotation locations
JSpecify type-use annotations have meaning only in recognized locations. Important recognized locations include method returns, formal parameters, fields, record components, type parameter upper bounds, non-wildcard type arguments, wildcard bounds, and array component types.

Common unrecognized locations:
- Class declarations: do not write `public @Nullable class Foo`.
- Type-parameter declarations or wildcard tokens: write `T extends @Nullable Object`, not `<@Nullable T>`; write `List<? extends @Nullable Object>`, not `List<@Nullable ?>`.
- Local-variable root types and cast root types. You may still annotate type arguments or array components inside those types.
- `instanceof`, pattern variables, thrown exception types, receiver parameters, and object/array creation root types.

## Array and nested-type placement
Array annotations attach to the component or the array reference depending on syntax:

```java
@NullMarked
final class TypeUseExamples {
  @Nullable String[] nullableElements;
  String @Nullable [] nullableArray;
  @Nullable String @Nullable [] nullableArrayAndElements;
  Map.@Nullable Entry<String, String> nullableEntry;

  void acceptNames(List<@Nullable String> names) {
    List<@Nullable String> copy = new ArrayList<>(names);
    copy.add(null);
  }
}
```

Avoid `@Nullable Foo.Bar`: it annotates the outer qualifier and is unrecognized by JSpecify. For a nullable nested type, write `Foo.@Nullable Bar`. For local variables, do not use root annotations like `@Nullable List<String> local`; use `List<@Nullable String>` when the elements are nullable.

## Generics and type variables
Inside `@NullMarked`, `<T>` is equivalent to `<T extends Object>` with a non-null upper bound. It does not allow `@Nullable` type arguments. Use a nullable bound when the abstraction must support nullable type arguments:

```java
@NullMarked
interface Box<T extends @Nullable Object> {
  T get();
  void set(T value);
}

@NullMarked
interface StrictBox<T> {
  T get();
}
```

Use annotations on a type-variable use only when that occurrence has different nullness than the type argument:

```java
@NullMarked
final class First {
  static <T> @Nullable T firstOrNull(List<T> values) {
    return values.isEmpty() ? null : values.get(0);
  }

  static <T extends @Nullable Object> T firstOrDefault(List<T> values, T defaultValue) {
    return values.isEmpty() ? defaultValue : values.get(0);
  }

  static <T extends @Nullable Object> Optional<@NonNull T> firstPresent(List<T> values) {
    for (T value : values) {
      if (value != null) {
        return Optional.of(value);
      }
    }
    return Optional.empty();
  }
}
```

Interpretation:
- `firstOrNull(List<String>)` may return `null` even though `T` is non-null.
- `firstOrDefault(List<T>, T)` mirrors the actual type argument; it accepts `List<@Nullable String>` only because the bound allows nullable type arguments.
- `Optional<@NonNull T>` documents that the optional payload, when present, is non-null even if `T` permits null.

## Migration notes
- From JSR-305, AndroidX, or other declaration annotations: update imports, then fix type-use placement for arrays, nested types, type arguments, and bounds.
- From Checker Framework nullness annotations: simple `@Nullable`/`@NonNull` imports often map directly, but Checker Framework has annotations outside JSpecify's API. Mixed annotations may remain necessary for checker-specific features.
- Before marking a Checker Framework-checked generic class as `@NullMarked`, add `T extends @Nullable Object` where existing clients must keep using nullable type arguments.
- For records, an `equals(Object)` parameter in a record class is treated specially by the spec; in null-marked source, annotate a manually written record `equals` parameter as `@Nullable Object`.

## Tooling and conformance
- JSpecify defines semantics, not mandatory diagnostics. Say "this type usage is nullable/non-null/unspecified by JSpecify" rather than "the tool must error."
- A conformant tool can still choose whether and how to report findings, and it may use extra facts to prove a dereference safe.
- `javac` alone type-checks annotation syntax but does not perform JSpecify nullness analysis.
- Use `jbang skills/jspecify-nullness/scripts/verify-examples.java` to compile and run the documented Java examples. Then run the project's configured JSpecify-aware checker for behavioral nullness feedback.

## Kotlin and annotation processors
- Kotlin users benefit because modern Kotlin compilers understand JSpecify-annotated Java APIs instead of treating every Java type as a platform type.
- JSpecify docs list Kotlin support milestones: `@Nullable` and `@NullMarked` from Kotlin 1.8.20, `@NonNull` from 2.0.0, `@NullUnmarked` from 2.0.20, and default JSpecify errors from 2.1.0.
- If Kotlin warnings are needed instead of errors, JSpecify docs cite `-Xnullability-annotations=@org.jspecify.annotations:warn`.
- Whole-program annotation processors that read type-use annotations from class files may require JDK 22+ `javac` because older `javac` versions had a type-use annotation reading bug.

## Checklist
- The JSpecify dependency is visible to consumers.
- `@NullMarked` is applied at an appropriate scope, with `@NullUnmarked` only for migration gaps.
- Nullable returns, parameters, fields, type arguments, and array components are annotated exactly where null is allowed.
- Each generic type parameter has an intentional bound.
- Local-variable and cast root annotations have been removed or moved to nested components.
- The code compiles, examples run, and a JSpecify-aware analyzer has checked the affected source and callers.

## Representative prompts
- "Annotate this Java API with JSpecify, including generics and call-site implications."
- "Migrate these JSR-305 or Checker Framework nullness annotations to JSpecify and fix type-use placement."
- "Decide whether this type parameter should be `<T>` or `<T extends @Nullable Object>` and explain the API contract."
- "Review this Java library for Kotlin consumers and JSpecify annotation-processor constraints."
