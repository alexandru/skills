---
name: scala-kindlings-derivation
description: Scala auto-derivation with Kindlings for Circe and PureConfig. Use when replacing circe-generic/circe-generic-extras or PureConfig generic derivation with Kindlings while keeping normal Circe JSON APIs and PureConfig loading/writing APIs.
---

# Scala Kindlings Derivation

## Quick start

- Use Kindlings to derive type class instances; keep using library APIs for actual work.
  - Circe: derive `Encoder`, `Decoder`, or `Codec.AsObject`; keep using `asJson`, `decode`, parsers, printers.
  - PureConfig: derive `ConfigReader`, `ConfigWriter`, or `ConfigConvert`; keep using `ConfigSource.load` and PureConfig writers.
- Prefer companion-object instances for root types used at call sites; nested product types are derived as needed.
- Configure derivation with Kindlings config values/hints, not with Circe/PureConfig generic imports.
- Do not import `io.circe.generic.auto._`, `io.circe.generic.semiauto._`, `pureconfig.generic.auto._`, or `pureconfig.generic.semiauto._` when using Kindlings.

## APIs to reach for

- Circe JSON:
  - Use `KindlingsEncoder.derive[A]`, `KindlingsDecoder.derive[A]`, or `KindlingsCodecAsObject.derive[A]`.
  - Cross-platform.
  - Default field names are unchanged.
  - ADTs are wrapped unless a discriminator is configured.
- PureConfig HOCON:
  - Use `KindlingsConfigReader.derive[A]`, `KindlingsConfigWriter.derive[A]`, or `KindlingsConfigConvert.derive[A]`.
  - JVM-only.
  - Defaults match PureConfig: kebab-case keys, `type` discriminator, defaults enabled, unknown keys allowed.

## References

- Load `references/circe-derivation.md` for Circe derivation, annotations, discriminators, and migration notes.
- Load `references/pureconfig-derivation.md` for PureConfig derivation, default conventions, discriminator configuration, and supported `PureConfig` knobs.
- Load `references/best-practices.md` for organization, call-site hygiene, and validation guidance.
