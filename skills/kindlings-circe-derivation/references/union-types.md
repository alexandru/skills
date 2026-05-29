# Union Types (Sealed Traits) with Kindlings Circe Derivation

## Discriminator-based derivation

For sealed trait hierarchies, use a discriminator field to distinguish between subtypes at runtime.

### With type discriminator and kebab-case constructor names

```scala
import hearth.kindlings.circederivation.{Configuration, KindlingsCodecAsObject}
import io.circe.Codec

sealed trait Animal
case class CatsForever(lives: Int) extends Animal
case class DogsForever(breed: String) extends Animal

object Animal {
  // Configure discriminator field "type" with kebab-case constructor names
  implicit val config: Configuration = Configuration()
    .withDiscriminator("type")
    .withKebabCaseConstructorNames

  implicit val codec: Codec[Animal] = KindlingsCodecAsObject.derive[Animal]
}

// Usage with Circe's API
import io.circe.parser.decode
import io.circe.syntax.EncoderOps

val cat: Animal = CatsForever(9)
cat.asJson.noSpaces  // {"type":"cats-forever","lives":9}

decode[Animal]("""{"type": "cats-forever", "lives": 9}""")  // Right(CatsForever(9))
```

### With type discriminator and lowercase constructor names

```scala
sealed trait Animal
case class Cat(name: String) extends Animal
case class Dog(breed: String) extends Animal

object Animal {
  implicit val config: Configuration = Configuration()
    .withDiscriminator("type")
    .withTransformConstructorNames(_.toLowerCase)
  implicit val codec: Codec[Animal] = KindlingsCodecAsObject.derive[Animal]
}

val cat: Animal = Cat("Whiskers")
cat.asJson.noSpaces  // {"type":"cat","name":"Whiskers"}

decode[Animal]("""{"type": "cat", "name": "Whiskers"}""")  // Right(Cat("Whiskers"))
```

## Shape-based discrimination (no discriminator field)

**Kindlings does NOT support pure shape-based discrimination natively.** If you want to encode/decode sealed traits based ONLY on the JSON structure (without any discriminator field or wrapper), you need to implement custom codecs. The cleanest approach is to derive subtype codecs using Kindlings and provide custom encoder/decoder for the sealed trait:

```scala
import hearth.kindlings.circederivation.KindlingsCodecAsObject
import io.circe.{Codec, Decoder, Encoder}
import io.circe.syntax.EncoderOps
import io.circe.parser.decode

sealed trait Shape
case class Circle(radius: Double) extends Shape
case class Rectangle(width: Double, height: Double) extends Shape
case class Square(side: Double) extends Shape

// Derive codecs for each subtype in their own companion objects
object Circle {
  implicit val codec: Codec[Circle] = KindlingsCodecAsObject.derive[Circle]
}
object Rectangle {
  implicit val codec: Codec[Rectangle] = KindlingsCodecAsObject.derive[Rectangle]
}
object Square {
  implicit val codec: Codec[Square] = KindlingsCodecAsObject.derive[Square]
}

object Shape {
  // Custom encoder: delegate to subtype encoders (no discriminator field)
  implicit val encoder: Encoder[Shape] = Encoder.instance {
    case c: Circle => c.asJson    // {"radius": 5.0}
    case r: Rectangle => r.asJson // {"width": 3.0, "height": 4.0}
    case s: Square => s.asJson     // {"side": 2.0}
  }

  // Custom decoder: try each decoder in order (shape-based discrimination)
  implicit val decoder: Decoder[Shape] =
    List[Decoder[Shape]](
      Decoder[Circle].map(identity(_)),
      Decoder[Rectangle].map(identity(_)),
      Decoder[Square].map(identity(_))
    ).reduceLeft(_ or _)
}

// Usage:
val circle: Shape = Circle(5.0)
circle.asJson.noSpaces  // {"radius":5.0}  - NO discriminator field!

decode[Shape]("""{"radius":5.0}""")  // Right(Circle(5.0))
decode[Shape]("""{"width":3.0,"height":4.0}""")  // Right(Rectangle(3.0,4.0))
decode[Shape]("""{"side":2.0}""")  // Right(Square(2.0))
```

**Important limitations:**
- **Requires non-overlapping fields**: Encoding is lossy without a discriminator. This only works reliably when each subtype has unique field names that don't overlap with other subtypes.
- **Decoding order matters**: The decoder tries subtypes in the order you specify with `reduceLeft(_ or _)`. If two subtypes could match the same JSON, the first one wins.
- **Not built into Kindlings**: This requires manual encoder/decoder implementation for the sealed trait, though subtype codecs can use Kindlings auto-derivation.

## Wrapper-style derivation

Without a discriminator, sealed traits use **wrapper-style** encoding by default, where each subtype is wrapped in a JSON object with the constructor name as the key:

**Note:** Wrapper-style encoding is different from discriminator-based encoding. With a discriminator, you get `{"type": "Circle", "radius": 5.0}`. With wrapper-style (no discriminator), you get `{"Circle": {"radius": 5.0}}`. Use discriminator-based encoding (see above) if you want inline fields with a type tag. Use shape-based discrimination (see above) if you want NO discriminator at all.

```scala
import hearth.kindlings.circederivation.KindlingsCodecAsObject
import io.circe.Codec

sealed trait Shape
case class Circle(radius: Double) extends Shape
case class Rectangle(width: Double, height: Double) extends Shape

object Shape {
  implicit val codec: Codec[Shape] = KindlingsCodecAsObject.derive[Shape]
}

// Note: Cast to Shape to use the Shape codec
val circle: Shape = Circle(5.0)
circle.asJson.noSpaces  // {"Circle":{"radius":5.0}}

val rectangle: Shape = Rectangle(3.0, 4.0)
rectangle.asJson.noSpaces  // {"Rectangle":{"width":3.0,"height":4.0}}

decode[Shape]("""{"Circle":{"radius":5.0}}""")  // Right(Circle(5.0))
```

**Note:** Kindlings also provides `.withoutDiscriminator` on `Configuration`, but this still uses wrapper-style encoding, not pure shape-based. For true shape-based discrimination without any wrapper, use the custom approach shown above.

## Available discriminator configurations

Use the fluent builder methods on `Configuration`:

| Method | Effect |
|--------|--------|
| `.withDiscriminator("type")` | Adds `{"type": "SubTypeName"}` field |
| `.withKebabCaseConstructorNames` | `CatsForever` -> `cats-forever` |
| `.withSnakeCaseConstructorNames` | `CatsForever` -> `cats_forever` |
| `.withPascalCaseConstructorNames` | `catsForever` -> `CatsForever` |
| `.withScreamingSnakeCaseConstructorNames` | `CatsForever` -> `CATS_FOREVER` |
| `.withTransformConstructorNames(f)` | Custom transformation |

## Nested sealed traits

Sealed traits can be nested within case classes. Each level can have its own discriminator:

```scala
sealed trait Pet
case class Cat(name: String) extends Pet
case class Dog(breed: String) extends Pet

case class Person(name: String, pet: Pet)

object Pet {
  implicit val config: Configuration = Configuration()
    .withDiscriminator("petType")
    .withTransformConstructorNames(_.toLowerCase)
  implicit val codec: Codec[Pet] = KindlingsCodecAsObject.derive[Pet]
}

object Person {
  implicit val codec: Codec[Person] = KindlingsCodecAsObject.derive[Person]
}

val person = Person("Alice", Cat("Whiskers"))
person.asJson.noSpaces
// {"name":"Alice","pet":{"petType":"cat","name":"Whiskers"}}

decode[Person]("""{"name":"Alice","pet":{"petType":"cat","name":"Whiskers"}}""")
// Right(Person("Alice", Cat("Whiskers")))
```

## Recursive types

Kindlings handles recursive types automatically - no lazy wrappers needed:

```scala
import hearth.kindlings.circederivation.KindlingsCodecAsObject
import io.circe.Codec

sealed trait Tree
case class Node(value: Int, children: List[Tree]) extends Tree
case class Leaf(value: Int) extends Tree

object Tree {
  implicit val config: Configuration = Configuration()
    .withDiscriminator("type")
  implicit val codec: Codec[Tree] = KindlingsCodecAsObject.derive[Tree]
}

// Works without Lazy or manual knot-tying
val tree: Tree = Node(1, List(Leaf(2), Node(3, List(Leaf(4)))))
tree.asJson.noSpaces
// {"type":"Node","value":1,"children":[{"type":"Leaf","value":2},{"type":"Node","value":3,"children":[{"type":"Leaf","value":4}]}]}

decode[Tree]("""{"type":"Node","value":1,"children":[{"type":"Leaf","value":2}]}""")
// Right(Node(1, List(Leaf(2))))
```
