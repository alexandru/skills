# Circe Derivation with Kindlings

Kindlings derives standard Circe instances. It does not replace Circe’s JSON AST, parser, printer, cursor, or syntax APIs.

## Derivation API

```scala
import hearth.kindlings.circederivation._
import io.circe.{Codec, Decoder, Encoder}

final case class User(name: String, age: Int)

object User {
  // Derive a codec when callers need both encoding and decoding.
  implicit val codec: Codec.AsObject[User] = KindlingsCodecAsObject.derive[User]
}
```

If a type is only encoded or only decoded, derive just that side:

```scala
val encoder: Encoder[User] = KindlingsEncoder.derive[User]
val decoder: Decoder[User] = KindlingsDecoder.derive[User]
```

Use Circe at call sites:

```scala
import io.circe.parser.decode
import io.circe.syntax.EncoderOps

User("Alice", 30).asJson.noSpaces
decode[User]("""{"name":"Bob","age":25}""")
```

## Configuration

`Configuration.default` uses unchanged member and constructor names, no defaults, no discriminator, non-strict decoding, and enum-as-object behavior unless configured.

Common knobs:

- Field-name transforms:
  - `withSnakeCaseMemberNames`
  - `withKebabCaseMemberNames`
  - `withPascalCaseMemberNames`
  - `withScreamingSnakeCaseMemberNames`
  - `withTransformMemberNames(f)` for a custom transform
- ADT constructor-name transforms:
  - `withSnakeCaseConstructorNames`
  - `withKebabCaseConstructorNames`
  - `withPascalCaseConstructorNames`
  - `withScreamingSnakeCaseConstructorNames`
  - `withTransformConstructorNames(f)` for a custom transform
- Missing fields:
  - `withDefaults` uses case-class defaults.
  - `withoutDefaults` requires fields to be present.
- ADT encoding:
  - `withDiscriminator(field)` uses an inline tag field.
  - `withoutDiscriminator` uses wrapped-subtype encoding.
- Unknown JSON fields:
  - `withStrictDecoding` rejects them.
  - `withoutStrictDecoding` ignores them.
- Enums:
  - `withEnumAsStrings` encodes Scala 3/Java enums as strings.

## Fields and transient fields

```scala
import hearth.kindlings.circederivation.KindlingsCodecAsObject
import hearth.kindlings.circederivation.annotations.{fieldName, transientField}
import io.circe.Codec

final case class ApiUser(
  @fieldName("user_name") name: String,
  @transientField cacheKey: String = "not-on-the-wire"
)

object ApiUser {
  implicit val codec: Codec.AsObject[ApiUser] = KindlingsCodecAsObject.derive[ApiUser]
}
```

Field annotations override global field-name transforms. A `@transientField` must have a default value so decoders can construct the value when the field is absent.

## Sealed traits

For public JSON, prefer a discriminator for stable, explicit ADT encoding:

```scala
import hearth.kindlings.circederivation.{Configuration, KindlingsCodecAsObject}
import io.circe.Codec

sealed trait Shape
final case class Circle(radius: Double) extends Shape
final case class Rectangle(width: Double, height: Double) extends Shape

object Shape {
  implicit val config: Configuration = Configuration.default
    .withDiscriminator("type")
    .withKebabCaseConstructorNames

  implicit val codec: Codec.AsObject[Shape] = KindlingsCodecAsObject.derive[Shape]
}
```

Without a discriminator, Kindlings uses wrapper-style ADT encoding such as `{"Circle":{"radius":5.0}}`. Shape-only decoding is not a built-in Kindlings mode; implement a custom Circe decoder only when you intentionally need that ambiguous style.

## Custom field types

For special fields, provide normal Circe instances and let Kindlings use them:

```scala
import hearth.kindlings.circederivation.KindlingsCodecAsObject
import io.circe.{Codec, Decoder, Encoder}
import java.time.Instant
import scala.util.Try

final case class Event(name: String, at: Instant)

object Event {
  implicit val instantEncoder: Encoder[Instant] = Encoder.encodeString.contramap(_.toString)
  implicit val instantDecoder: Decoder[Instant] = Decoder.decodeString.emap { value =>
    Try(Instant.parse(value)).toEither.left.map(_.getMessage)
  }
  implicit val codec: Codec.AsObject[Event] = KindlingsCodecAsObject.derive[Event]
}
```
