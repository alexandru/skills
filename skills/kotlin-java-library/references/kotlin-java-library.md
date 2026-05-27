# Kotlin Java Library Design - Reference

Use this when Kotlin public APIs must be pleasant and stable for Java callers.

Sources:
- https://kotlinlang.org/docs/java-to-kotlin-interop.html
- https://kotlinlang.org/docs/jvm-records.html
- https://kotlinlang.org/docs/api-guidelines-backward-compatibility.html
- https://developer.android.com/kotlin/interop
- https://proandroiddev.com/everything-about-jvmfield-jvmoverloads-jvmname-and-jvmstatic-annotations-in-kotlin-158383081cb8

## Table of Contents
- [Source takeaways](#source-takeaways)
- [Interop goals](#interop-goals)
- [Type-checked sample](#type-checked-sample)
- [JVM annotation guidance](#jvm-annotation-guidance)
- [JVM records](#jvm-records)
- [Backward compatibility rules](#backward-compatibility-rules)
- [Android and bidirectional interop](#android-and-bidirectional-interop)
- [Checklist](#checklist)
- [Test prompts](#test-prompts)

## Source takeaways
- Kotlin top-level declarations become static methods on a generated facade class; use `@file:JvmName` for stable Java names and `@file:JvmMultifileClass` when several files should share one facade.
- `@JvmOverloads` generates Java overloads for default parameters, but it does not preserve binary compatibility when adding parameters to an existing published function.
- Companion/object functions need `@JvmStatic` for direct static Java calls. Non-`const` companion constants need `@JvmField` for direct static field access.
- Kotlin checked exceptions are not declared to Java unless the Kotlin function uses `@Throws`.
- Kotlin variance normally creates Java wildcards for parameter positions and avoids them for return positions; use `@JvmSuppressWildcards` and `@JvmWildcard` only when the generated Java signature is wrong for callers.
- `@JvmRecord` requires a record-capable JVM target and is not binary compatible when applied to an already published class.
- For public APIs, explicit return types, manual overloads, and avoiding public `data class` evolution hazards matter more than Kotlin concision.

## Interop goals
- Make the Java surface explicit and stable: class names, method names, overloads, nullability, exceptions, and fields should be unsurprising.
- Prefer predictable JVM signatures over Kotlin-only conveniences for published APIs.
- Include Java call-site examples for every non-trivial public entry point.
- Verify examples by compiling Kotlin code and Java callers together before publishing guidance.

## Type-checked sample

The examples in this section are covered by `../scripts/verify-examples.java`. From the repository root, run:

```bash
jbang skills/kotlin-java-library/scripts/verify-examples.java
```

The script writes the Kotlin API and Java client to a temporary directory, compiles the Kotlin API with `kotlinc -jvm-target 17`, compiles the Java caller with `javac`, then runs the Java client.

### Kotlin API

```kotlin
@file:JvmName("LibraryApis")

package com.example.library

import java.io.IOException
import java.nio.file.Files
import java.nio.file.Path
import java.util.Collections

class Client @JvmOverloads constructor(
    val endpoint: String,
    val timeoutMillis: Long = 2_000,
    val retries: Int = 1,
) {
    fun describe(): String = "$endpoint:$timeoutMillis:$retries"
}

@JvmOverloads
fun connect(host: String, port: Int = 443, secure: Boolean = true): String =
    "$host:$port?secure=$secure"

class Ids private constructor() {
    companion object {
        const val DEFAULT_PREFIX: String = "usr"

        @JvmField
        val MAX_ID_LENGTH: Int = 36

        @JvmStatic
        @JvmOverloads
        fun newId(prefix: String = DEFAULT_PREFIX): String =
            "$prefix-0001"
    }
}

fun interface NameFormatter {
    fun format(name: String): String
}

fun greeting(name: String, formatter: NameFormatter): String =
    formatter.format(name)

@Throws(IOException::class)
fun readFirstLine(path: Path): String =
    Files.readAllLines(path).firstOrNull() ?: ""

fun readOnlyNames(names: List<String>): List<String> =
    Collections.unmodifiableList(names.toList())

@JvmName("displayStrings")
fun List<String>.display(): String = joinToString(",")

@JvmName("displayInts")
fun List<Int>.display(): String = joinToString(":")

@JvmRecord
data class UserId(val value: String)

interface Base {
    val id: String
}

class Derived(override val id: String) : Base

class Box<out T>(val value: T)

fun baseId(box: Box<Base>): String = box.value.id

fun exactBaseId(box: Box<@JvmSuppressWildcards Base>): String =
    box.value.id
```

### Java call site

```java
import com.example.library.Base;
import com.example.library.Box;
import com.example.library.Client;
import com.example.library.Derived;
import com.example.library.Ids;
import com.example.library.LibraryApis;
import com.example.library.UserId;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

public class JavaClient {
    public static void main(String[] args) throws Exception {
        Client defaultClient = new Client("https://api.example.com");
        Client customClient = new Client("https://api.example.com", 5_000L, 2);
        require(defaultClient.describe().equals("https://api.example.com:2000:1"));
        require(customClient.describe().equals("https://api.example.com:5000:2"));

        require(LibraryApis.connect("example.com").equals("example.com:443?secure=true"));
        require(LibraryApis.connect("example.com", 8443, false).equals("example.com:8443?secure=false"));

        require(Ids.DEFAULT_PREFIX.equals("usr"));
        require(Ids.MAX_ID_LENGTH == 36);
        require(Ids.newId().equals("usr-0001"));
        require(Ids.newId("admin").equals("admin-0001"));

        String greeting = LibraryApis.greeting("Ada", name -> "Hello, " + name);
        require(greeting.equals("Hello, Ada"));

        Path config = Files.createTempFile("config", ".txt");
        Files.writeString(config, "first\nsecond\n");
        try {
            require(LibraryApis.readFirstLine(config).equals("first"));
        } catch (IOException e) {
            throw new AssertionError(e);
        } finally {
            Files.deleteIfExists(config);
        }

        List<String> names = LibraryApis.readOnlyNames(List.of("Ada", "Grace"));
        require(names.size() == 2);
        try {
            names.add("Katherine");
            throw new AssertionError("readOnlyNames should be unmodifiable");
        } catch (UnsupportedOperationException expected) {
            // Expected.
        }

        require(LibraryApis.displayStrings(List.of("a", "b")).equals("a,b"));
        require(LibraryApis.displayInts(List.of(1, 2)).equals("1:2"));

        UserId userId = new UserId("u-1");
        require(userId.value().equals("u-1"));

        require(LibraryApis.baseId(new Box<Derived>(new Derived("d-1"))).equals("d-1"));
        require(LibraryApis.exactBaseId(new Box<Base>(new Derived("b-1"))).equals("b-1"));
    }

    private static void require(boolean condition) {
        if (!condition) {
            throw new AssertionError();
        }
    }
}
```

## JVM annotation guidance

### `@file:JvmName` and `@file:JvmMultifileClass`
- Add `@file:JvmName("StableName")` to files with Java-callable top-level declarations.
- Use `@file:JvmMultifileClass` only when multiple Kotlin files in the same package should intentionally share one Java facade.
- Keep facade names stable after publishing; renaming the facade is a Java binary/source break.

### `@JvmOverloads`
- Use for constructors or methods where Java callers need defaulted arguments.
- Do not rely on it to evolve existing APIs. If adding a parameter to a published function, keep the old signature as a manual overload.
- Prefer explicit overloads when Java behavior should differ from Kotlin defaults or when overloads of same-typed parameters would be ambiguous.

### `@JvmStatic`, `const val`, and `@JvmField`
- Use `@JvmStatic` for companion/object functions meant to be called as `Type.method()`.
- Use `const val` for compile-time constants.
- Use `@JvmField` for immutable non-`const` fields that should be accessed as `Type.FIELD`. Once Java callers use a field, changing it to a property accessor is binary-incompatible.

### `@JvmName`
- Use on functions or accessors to resolve erased-signature clashes.
- Use file-level `@JvmName` to choose a stable facade class for top-level functions.
- Prefer clear Java names over preserving Kotlin extension-style naming in Java.

### `@Throws`
- Use for checked exceptions that Java callers are expected to catch.
- Kotlin callers do not need the annotation, so add it based on Java API needs.

### Generics and wildcards
- Start with Kotlin's default wildcard generation and inspect the Java signature.
- Use `@JvmSuppressWildcards` when the generated `? extends` or `? super` signature is needlessly hard for Java callers.
- Use `@JvmWildcard` when Java needs a wildcard in a return position where Kotlin does not generate one by default.
- Avoid `Nothing` in public generic signatures because Java sees raw types.

### Inline value classes
- Avoid exposing Kotlin value classes directly to Java unless the Java surface is verified.
- If Java must construct or pass value classes, use `@JvmExposeBoxed` or `-Xjvm-expose-boxed` only with the required opt-in and a compiled Java call-site test.

## JVM records
- Use `@JvmRecord` only on data classes that are intended to be Java records from the start.
- Target JVM 16 or newer. The class cannot have mutable backing-field properties or extra backing fields beyond primary constructor `val` properties.
- Java callers use record component accessors such as `userId.value()`, not Kotlin property getter names.
- Applying `@JvmRecord` to an existing class changes property accessor naming and is not binary compatible.

## Backward compatibility rules
- Explicitly declare public function return types and property types.
- Do not change or remove public API members once published; add new members and deprecate old ones.
- Do not add parameters to existing public functions unless the old signature remains as a manual overload.
- Adding `@JvmOverloads` or default arguments after publication does not automatically preserve old JVM signatures.
- Changing type, nullability, package, class name, member name, or generic arity is a compatibility risk.
- Changing a property to a function, or a function to a property, breaks Java callers.
- Avoid public `data class` types when constructor or `copy` evolution is likely.
- Treat `@PublishedApi` declarations as public API because compiled client code may reference them.
- Use a deprecation cycle (`WARNING` -> `ERROR` -> `HIDDEN`) before removal.
- For real libraries, add binary compatibility validation to CI in addition to Java call-site compilation.

## Android and bidirectional interop
- Public Java APIs consumed from Kotlin should annotate every non-primitive parameter, return, and field with nullability annotations.
- Put SAM-convertible callback parameters last so Kotlin callers can use trailing lambda syntax.
- Use bean-style accessors (`get`, `is`, `set`) when Java methods should appear as Kotlin properties.
- Do not expose Kotlin function types returning `Unit` to Java callers; Java code then has to return `Unit.INSTANCE`.
- Prefer `fun interface` for callback contracts that should work naturally from Java and Kotlin.
- Return defensive copies or unmodifiable views for read-only collections because Kotlin read-only collection interfaces do not make Java views immutable.

## Checklist
- Public API names and facade names are stable and Java-friendly.
- Java call-site examples compile for every public entry point.
- `@JvmOverloads`, `@JvmStatic`, `@JvmField`, `@JvmName`, `@Throws`, and `@JvmRecord` are used intentionally.
- Public return/property types are explicit.
- Checked exceptions, nullability, overload behavior, and collection mutability are clear to Java callers.
- No public API change breaks binary compatibility without a deprecation/migration plan.
- `scripts/verify-examples.java` passes after sample or guidance changes.

## Test prompts
- "Design a Kotlin API for a Java SDK with optional args and stable overloads."
- "Make this Kotlin utility Java-friendly using JVM annotations and show Java call sites."
- "Audit this Kotlin public API for backward-compatibility risks and propose fixes."
- "Model a value object as a Java record using Kotlin; list the constraints."
