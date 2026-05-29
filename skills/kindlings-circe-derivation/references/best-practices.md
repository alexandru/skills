# Best Practices for Kindlings Circe Derivation

## Core Principle

**Kindlings can work with automatic derivation, and codecs should only be defined when it matters.**

Automatic derivation is the default and preferred approach. Explicit codec definitions are only necessary for:
- Customizations (discriminators, field name transforms, etc.)
- Types that Kindlings cannot auto-derive (rare edge cases)
- Types actually encoded/decoded at call sites

## When to Define Codecs Explicitly

### ✅ DO define codecs when:

1. **Customizing encoding/decoding behavior**
   ```scala
   import hearth.kindlings.circederivation.{Configuration, KindlingsCodecAsObject}
   import io.circe.Codec
   
   sealed trait Animal
   case class Cat(name: String) extends Animal
   
   object Animal {
     // Custom discriminator configuration with kebab-case constructor names
     implicit val config: Configuration = Configuration()
       .withDiscriminator("type")
       .withKebabCaseConstructorNames
     
     implicit val codec: Codec[Animal] = KindlingsCodecAsObject.derive[Animal]
   }
   ```

2. **Type is used at Circe encoding/decoding call sites**
   
   Call sites are places where you use Circe's API (`asJson`, `decode`, etc.):
   ```scala
   import io.circe.parser.decode
   import io.circe.syntax.EncoderOps
   
   // Person needs to have a visible Encoder/Decoder in scope for these to work
   val p = Person("Alice", 30)
   p.asJson           // Requires Encoder[Person]
   decode[Person](jsonString)  // Requires Decoder[Person]
   ```

3. **Type has special requirements** (useDefaults, strictDecoding, etc.)
   ```scala
   case class Config(defaultValue: String = "default")
   
   object Config {
     implicit val config: Configuration = Configuration(useDefaults = true)
     implicit val codec: Codec[Config] = KindlingsCodecAsObject.derive[Config]
   }
   ```

### ❌ DON'T define codecs when:

1. **Nested types that are only used within another codec**
   ```scala
   case class MyCode(value: String)
   case class MyAddress(street: String, country: String)
   
   case class Person(
     name: String,
     code: MyCode,
     address: MyAddress
   )
   
   // DO define codec for Person (used at call site)
   object Person {
     implicit val codec: Codec[Person] = KindlingsCodecAsObject.derive[Person]
   }
   
   // DON'T define codecs for MyCode and MyAddress
   // - They are derived automatically when Person's codec is derived
   // - Defining them explicitly adds unnecessary boilerplate
   ```

2. **Relying on extra imports at Circe call sites**
   
   Call sites are places where you use Circe's API methods like `asJson`, `decode`, `EncoderOps`, etc.:
   
   ```scala
   // ❌ BAD - Having extra imports here just for codecs is a code smell
   import io.circe.parser.decode
   import com.example.codecs.AllMyCodecs._  // Extra import only needed for decoding
   
   decode[MyType](json)  // This call site requires Encoder[MyType] to be in scope
   
   // ✅ GOOD - Decoder/Encoder should be in scope via companion object or package object
   import io.circe.parser.decode
   
   // MyType's decoder is available because:
   // - It's defined in MyType's companion object, which is imported automatically, OR
   // - It's defined in a package object that's already in scope
   decode[MyType](json)
   ```
   
   **Why this is a code smell:** If your call site needs a specific import just to make encoding/decoding work (beyond the standard Circe imports), it suggests the codec definitions are not organized properly. Codecs should be discoverable through normal Scala import mechanisms (companion objects, package objects) without requiring special imports at every usage site.

## Code Organization

### Preferred: Companion Object Pattern

```scala
case class Person(name: String, age: Int)

object Person {
  implicit val codec: Codec[Person] = KindlingsCodecAsObject.derive[Person]
}

// Usage - codec is automatically in scope
import io.circe.parser.decode
import io.circe.syntax.EncoderOps

val p = Person("Alice", 30)
p.asJson  // Uses Person.codec implicitly
decode[Person](json)  // Uses Person.codec implicitly
```

### Alternative: Package Object for Related Types

```scala
// In package.scala or a package object
package com.example.models

implicit val personCodec: Codec[Person] = KindlingsCodecAsObject.derive[Person]
implicit val addressCodec: Codec[Address] = KindlingsCodecAsObject.derive[Address]
```

## Working with Nested Types

Nested types within a codec **do not need explicit codecs** — Kindlings derives them automatically:

```scala
case class MyCode(value: String)
case class MyAddress(street: String, country: String)

case class Person(
  name: String,
  code: MyCode,
  address: MyAddress
)

object Person {
  // Only Person needs an explicit codec
  // MyCode and MyAddress are derived automatically
  implicit val codec: Codec[Person] = KindlingsCodecAsObject.derive[Person]
}

// This works - nested types are handled automatically
val json = """{ "name": "John", "code": { "value": "123" }, "address": { "street": "123 Main St", "country": "USA" } }"""
decode[Person](json)
```

## Performance Considerations

Kindlings' "sanely-automatic" derivation:
- Derives instances once and reuses them when a type is used in multiple places
- Is effectively free (no different from hand-written) when a type is used in only one place
- No need to manually cache or memoize codecs

## Testing

When testing codecs, prefer property-based tests with ScalaCheck or explicit round-trip tests:

```scala
// Round-trip test
val person = Person("Alice", 30)
val json = person.asJson.noSpaces
val decoded = decode[Person](json).valueOr(throw _)
assert(decoded == person)

// Parsing test with missing optional fields
decode[Person]("""{"name": "Bob"}""").valueOr(throw _)  // Should use default for age
```

## Migration from circe-generic

| circe-generic | Kindlings |
|---------------|-----------|
| `import io.circe.generic.auto._` | Remove - use explicit derivation |
| `import io.circe.generic.semiauto._` | Use `KindlingsEncoder.derive` / `KindlingsDecoder.derive` |
| `@ConfiguredJsonCodec` | Use `KindlingsCodecAsObject.derive` with Configuration |
| Shapeless-based | Hearth-based (faster compilation, better errors) |

## Error Handling

Kindlings produces clear, actionable error messages. If derivation fails, the error will tell you exactly which type is missing an instance and where in the type hierarchy the problem occurs.

Example error:
```
No given instance of type io.circe.Encoder[MyType] was found for parameter encoder of method asJson
  in class EncoderOps.

This typically means:
1. You forgot to define an Encoder[MyType] (or it's not in scope)
2. MyType is a sealed trait that needs a Configuration with discriminator
3. A nested type within MyType is missing its codec
```

To fix, add the missing codec in the companion object of the type.
