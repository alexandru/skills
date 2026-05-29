---
name: kindlings-circe-derivation
description: Type class derivation for Circe using Kindlings. Use when you need to derive Encoder/Decoder/Codec instances for Circe JSON serialization with support for case classes, sealed traits, nested types, and customizations like discriminator fields, field name transforms, and default values.
---

# Kindlings Circe Derivation

## Quick start

- Use `KindlingsEncoder.derive[T]` and `KindlingsDecoder.derive[T]` to create Circe-compatible instances
- For sealed traits, add `implicit val config: Configuration` in companion with discriminator/styling options
- Define codecs explicitly only for customization or when automatic derivation fails
- Always use Circe's API (`asJson`, `decode`) for encoding/decoding
- Avoid extra imports at call sites that use Circe's `Encoder`/`Decoder` — this is a code smell

## When to define codecs explicitly

- **For customizations** (custom field names, discriminators, etc.)
- **For types actually encoded/decoded at call-sites** (ensure instances are in scope)
- **When Kindlings can't auto-derive** (newtypes, special cases)
- **Nested types** in a codec don't need explicit instances — they can be derived automatically

## References

- Load `references/union-types.md` for sealed trait derivation with discriminators
- Load `references/field-customization.md` for custom field names and transformations
- Load `references/best-practices.md` for when to use automatic vs semi-automatic derivation
