# Best Practices for Scala Kindlings Derivation

## Core principle

Kindlings replaces only the generic derivation layer. It derives standard ecosystem type classes:

- Circe: `Encoder`, `Decoder`, `Codec.AsObject`
- PureConfig: `ConfigReader`, `ConfigWriter`, `ConfigConvert`

Keep application code on Circe/PureConfig APIs. If a call site needs special imports only to discover derived instances, move the instance to a companion object, package object, or the existing project-wide instance module.

## When to define instances explicitly

Define a top-level instance when:

- The type is encoded/decoded/loaded/written directly at call sites.
- The type needs custom derivation settings: discriminator, field/key annotation, defaults, strict decoding, naming transforms.
- You are publishing a stable API and want compile errors at the type definition, not at distant call sites.

Do not define boilerplate instances for every nested case class. Kindlings can derive nested product types while deriving the root type.

## Preferred organization

```scala
import hearth.kindlings.circederivation.KindlingsCodecAsObject
import io.circe.Codec

final case class Address(street: String, country: String)
final case class Person(name: String, address: Address)

object Person {
  implicit val codec: Codec.AsObject[Person] = KindlingsCodecAsObject.derive[Person]
}
```

`Address` does not need a visible codec unless callers also encode/decode `Address` directly.

## Migration map

- Replacing `io.circe.generic.auto._`:
  - Prefer companion/package instances using `Kindlings*`.
  - Use Kindlings sanely-automatic derivation only where that pattern is already established.
- Replacing `io.circe.generic.semiauto._`:
  - Use `KindlingsEncoder.derive`, `KindlingsDecoder.derive`, or `KindlingsCodecAsObject.derive`.
- Replacing `@ConfiguredJsonCodec`:
  - Define an explicit `Configuration` and derive with `KindlingsCodecAsObject.derive`.
- Replacing `pureconfig.generic.auto._` or `pureconfig.generic.semiauto._`:
  - Use `KindlingsConfigReader.derive`, `KindlingsConfigWriter.derive`, or `KindlingsConfigConvert.derive`.
- Replacing `pureconfig.derivation.default.*`:
  - Use Kindlings derivation.
  - Add `PureConfig`/hints only when PureConfig defaults are not enough.

## Validation

- Compile samples with the same Scala major version and Kindlings modules they document.
- For JSON/config behavior, run at least one encode/decode or load/write assertion, not just type checking.
- This skill’s representative snippets are validated by `scripts/verify-examples.scala`.
