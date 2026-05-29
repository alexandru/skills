# PureConfig Derivation with Kindlings

Kindlings derives standard PureConfig instances on the JVM. It does not replace HOCON parsing, `ConfigSource`, `ConfigReader`/`ConfigWriter` usage, or PureConfig error reporting.

## Derivation API

```scala
import hearth.kindlings.pureconfigderivation._
import pureconfig.{ConfigConvert, ConfigReader, ConfigWriter}

final case class ServerConfig(host: String, port: Int = 8080)

val reader: ConfigReader[ServerConfig] = KindlingsConfigReader.derive[ServerConfig]
val writer: ConfigWriter[ServerConfig] = KindlingsConfigWriter.derive[ServerConfig]
val convert: ConfigConvert[ServerConfig] = KindlingsConfigConvert.derive[ServerConfig]
```

Use PureConfig at call sites:

```scala
import pureconfig.ConfigSource

ConfigSource.string("""
  host = "localhost"
  port = 8080
""").load[ServerConfig](reader)
```

## Defaults match PureConfig conventions

`PureConfig.default` uses upstream PureConfig defaults:

- case-class fields: `camelCase` Scala names map to `kebab-case` HOCON keys.
- ADT constructors: `PascalCase` subtype names map to `kebab-case` discriminator values.
- discriminator field: `type`.
- case-class default values are used for missing keys.
- unknown keys are allowed.

Most projects should not configure naming for PureConfig; rely on kebab-case unless a codebase already standardized on a different convention. The common customization is the ADT discriminator field.

## Discriminator configuration for sealed traits

```scala
import hearth.kindlings.pureconfigderivation.{KindlingsConfigReader, PureConfig}
import pureconfig.ConfigReader

sealed trait Backend
final case class Postgres(host: String, port: Int) extends Backend
final case class Sqlite(path: String) extends Backend

object Backend {
  implicit val config: PureConfig = PureConfig.default.withDiscriminator("backend")
  implicit val reader: ConfigReader[Backend] = KindlingsConfigReader.derive[Backend]
}
```

HOCON uses kebab-case constructor values by default:

```hocon
backend = "postgres"
host = "db.internal"
port = 5432
```

No shape-based union decoding is needed for normal PureConfig usage. If you want no discriminator, Kindlings supports wrapped subtypes via `withWrappedSubtypes`, but prefer a discriminator for readable configuration.

## What `PureConfig` supports

- Field-name transforms:
  - Default: kebab-case HOCON keys.
  - `withSnakeCaseMemberNames`
  - `withKebabCaseMemberNames`
  - `withPascalCaseMemberNames`
  - `withScreamingSnakeCaseMemberNames`
  - `withCamelCaseMemberNames`
  - `withTransformMemberNames(f)` for a custom transform
- ADT constructor-name transforms:
  - Default: kebab-case discriminator values.
  - `withSnakeCaseConstructorNames`
  - `withKebabCaseConstructorNames`
  - `withTransformConstructorNames(f)` for a custom transform
- ADT representation:
  - `withDiscriminator(field)` uses a discriminator field; default is `type`.
  - `withWrappedSubtypes` disables the discriminator and uses single-key wrapped subtypes.
- Missing keys:
  - `withUseDefaults` uses case-class defaults; this is the default.
  - `withoutUseDefaults` requires keys to be present.
- Unknown keys:
  - `withAllowUnknownKeys` ignores them; this is the default.
  - `withStrictDecoding` fails on them.

Per-type overrides are available through `KindlingsProductHint[A]` and `KindlingsCoproductHint[A]`, but prefer the global `PureConfig` unless only one type differs.

## Field annotations

```scala
import hearth.kindlings.pureconfigderivation.KindlingsConfigReader
import hearth.kindlings.pureconfigderivation.annotations.{configKey, transientField}
import pureconfig.ConfigReader

final case class DatabaseConfig(
  @configKey("jdbc-url") jdbcUrl: String,
  @transientField cachedPoolName: Option[String] = None
)

object DatabaseConfig {
  implicit val reader: ConfigReader[DatabaseConfig] = KindlingsConfigReader.derive[DatabaseConfig]
}
```

`@configKey` overrides the HOCON key for a field. `@transientField` excludes a field from reading/writing and must have a default value.
