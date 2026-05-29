# Field Customization with Kindlings Circe Derivation

## Per-field name annotation

Use `@fieldName` annotation to customize JSON field names for individual fields:

```scala
import hearth.kindlings.circederivation.annotations.fieldName
import hearth.kindlings.circederivation.KindlingsCodecAsObject
import io.circe.Codec
import io.circe.syntax.EncoderOps

case class User(
  @fieldName("user_name") name: String,
  @fieldName("user_age") age: Int,
  email: String  // Uses default field name
)

object User {
  implicit val codec: Codec[User] = KindlingsCodecAsObject.derive[User]
}

User("Alice", 30, "alice@example.com").asJson.noSpaces
// {"user_name":"Alice","user_age":30,"email":"alice@example.com"}
```

## Global field name transformations

Apply transformations to all field names in a type using built-in helpers:

```scala
import hearth.kindlings.circederivation.{Configuration, KindlingsCodecAsObject}
import io.circe.Codec
import io.circe.syntax.EncoderOps

case class Person(firstName: String, lastName: String, dateOfBirth: String)

object Person {
  implicit val config: Configuration = Configuration()
    .withSnakeCaseMemberNames
  implicit val codec: Codec[Person] = KindlingsCodecAsObject.derive[Person]
}

Person("Alice", "Smith", "1990-01-01").asJson.noSpaces
// {"first_name":"Alice","last_name":"Smith","date_of_birth":"1990-01-01"}
```

## Available transformation helpers

Use the built-in helper methods on `Configuration`:

| Helper Method | Transforms | Example |
|---------------|------------|---------|
| `.withSnakeCaseMemberNames` | `firstName` → `first_name` | Fields |
| `.withKebabCaseMemberNames` | `firstName` → `first-name` | Fields |
| `.withPascalCaseMemberNames` | `firstName` → `FirstName` | Fields |
| `.withScreamingSnakeCaseMemberNames` | `firstName` → `FIRST_NAME` | Fields |
| `.withSnakeCaseConstructorNames` | `MyType` → `my_type` | Constructor names |
| `.withKebabCaseConstructorNames` | `MyType` → `my-type` | Constructor names |
| `.withPascalCaseConstructorNames` | `myType` → `MyType` | Constructor names |
| `.withScreamingSnakeCaseConstructorNames` | `MyType` → `MY_TYPE` | Constructor names |
| `.withTransformMemberNames(f)` | Custom | Any `String => String` |
| `.withTransformConstructorNames(f)` | Custom | Any `String => String` |

For custom transformations, use `.withTransformMemberNames` or `.withTransformConstructorNames`:

```scala
implicit val config: Configuration = Configuration()
  .withTransformConstructorNames(_.toLowerCase)
```

## Combining per-field and global transformations

Per-field annotations take precedence over global transformations:

```scala
import hearth.kindlings.circederivation.{Configuration, KindlingsCodecAsObject}
import hearth.kindlings.circederivation.annotations.fieldName
import io.circe.Codec
import io.circe.syntax.EncoderOps

case class Product(
  @fieldName("id") productId: String,
  productName: String,
  unitPrice: Double
)

object Product {
  implicit val config: Configuration = Configuration()
    .withSnakeCaseMemberNames
  implicit val codec: Codec[Product] = KindlingsCodecAsObject.derive[Product]
}

Product("123", "Widget", 9.99).asJson.noSpaces
// {"id":"123","product_name":"Widget","unit_price":9.99}
// Note: productId uses "id" (from annotation), not "product_id" (from global transform)
```

## Transient fields

Mark fields as transient to exclude them from serialization/deserialization. The field must have a default value:

```scala
import hearth.kindlings.circederivation.annotations.transientField
import hearth.kindlings.circederivation.KindlingsCodecAsObject
import io.circe.Codec
import io.circe.syntax.EncoderOps
import io.circe.parser.decode

case class SensitiveData(
  publicInfo: String,
  @transientField internalId: String = "hidden"
)

object SensitiveData {
  implicit val codec: Codec[SensitiveData] = KindlingsCodecAsObject.derive[SensitiveData]
}

SensitiveData("Hello", "secret-123").asJson.noSpaces
// {"publicInfo":"Hello"}  // internalId is excluded

decode[SensitiveData]("""{"publicInfo":"Hi"}""")
// Right(SensitiveData("Hi", "hidden"))  // Uses default value
```

## Custom encoder/decoder for specific fields

For fields that need special handling, provide custom Encoder/Decoder instances:

```scala
import java.time.Instant
import io.circe.{Codec, Encoder, Decoder}
import hearth.kindlings.circederivation.KindlingsCodecAsObject
import io.circe.syntax.EncoderOps

case class Event(name: String, timestamp: Instant)

object Event {
  // Custom Encoder for Instant
  implicit val instantEncoder: Encoder[Instant] = Encoder.encodeString.contramap(_.toString)
  
  // Custom Decoder for Instant
  implicit val instantDecoder: Decoder[Instant] = Decoder.decodeString.emap { str =>
    Either.catchOnly[Exception](Instant.parse(str)).leftMap(_.getMessage)
  }

  implicit val codec: Codec[Event] = KindlingsCodecAsObject.derive[Event]
}

Event("Launch", Instant.now()).asJson.noSpaces
// {"name":"Launch","timestamp":"2024-01-15T10:30:00Z"}
```
