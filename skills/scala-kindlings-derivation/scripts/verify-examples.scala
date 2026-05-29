#!/usr/bin/env -S scala shebang -q

//> using scala "3.8.3"
//> using options "-no-indent"
//> using dep "com.kubuszok::kindlings-circe-derivation:0.1.2"
//> using dep "com.kubuszok::kindlings-pureconfig-derivation:0.1.2"
//> using dep "io.circe::circe-parser:0.14.15"

import hearth.kindlings.circederivation.{Configuration, KindlingsCodecAsObject}
import hearth.kindlings.pureconfigderivation.{KindlingsConfigConvert, KindlingsConfigReader, KindlingsConfigWriter, PureConfig}
import io.circe.parser.decode
import io.circe.syntax.EncoderOps
import io.circe.{Codec, Decoder, Encoder}
import pureconfig.{ConfigConvert, ConfigReader, ConfigSource, ConfigWriter}
import scala.util.Try

object CirceExamples {
  import hearth.kindlings.circederivation.annotations.{fieldName, transientField}

  final case class User(name: String, age: Int)
  object User {
    implicit val codec: Codec.AsObject[User] = KindlingsCodecAsObject.derive[User]
  }

  final case class ApiUser(
    @fieldName("user_name") name: String,
    @transientField cacheKey: String = "not-on-the-wire"
  )
  object ApiUser {
    implicit val codec: Codec.AsObject[ApiUser] = KindlingsCodecAsObject.derive[ApiUser]
  }

  sealed trait Shape
  final case class Circle(radius: Double) extends Shape
  final case class Rectangle(width: Double, height: Double) extends Shape
  object Shape {
    implicit val config: Configuration = Configuration.default
      .withDiscriminator("type")
      .withKebabCaseConstructorNames
    implicit val codec: Codec.AsObject[Shape] = KindlingsCodecAsObject.derive[Shape]
  }

  final case class Event(name: String, at: java.time.Instant)
  object Event {
    implicit val instantEncoder: Encoder[java.time.Instant] = Encoder.encodeString.contramap(_.toString)
    implicit val instantDecoder: Decoder[java.time.Instant] = Decoder.decodeString.emap { value =>
      Try(java.time.Instant.parse(value)).toEither.left.map(_.getMessage)
    }
    implicit val codec: Codec.AsObject[Event] = KindlingsCodecAsObject.derive[Event]
  }

  def verify(): Unit = {
    assert(User("Alice", 30).asJson.noSpaces == """{"name":"Alice","age":30}""")
    assert(decode[User]("""{"name":"Bob","age":25}""").contains(User("Bob", 25)))
    assert(ApiUser("Alice", "secret").asJson.noSpaces == """{"user_name":"Alice"}""")
    assert(decode[ApiUser]("""{"user_name":"Bob"}""").contains(ApiUser("Bob")))
    val shape: Shape = Circle(5.0)
    assert(shape.asJson.noSpaces == """{"type":"circle","radius":5.0}""")
    assert(decode[Shape]("""{"type":"rectangle","width":3.0,"height":4.0}""").contains(Rectangle(3.0, 4.0)))
    val event = Event("launch", java.time.Instant.parse("2026-01-01T00:00:00Z"))
    assert(decode[Event](event.asJson.noSpaces).contains(event))
  }
}

object PureConfigExamples {
  import hearth.kindlings.pureconfigderivation.annotations.{configKey, transientField}

  final case class ServerConfig(host: String, port: Int = 8080)
  object ServerConfig {
    implicit val reader: ConfigReader[ServerConfig] = KindlingsConfigReader.derive[ServerConfig]
    implicit val writer: ConfigWriter[ServerConfig] = KindlingsConfigWriter.derive[ServerConfig]
    val convert: ConfigConvert[ServerConfig] = KindlingsConfigConvert.derive[ServerConfig]
  }

  sealed trait Backend
  final case class Postgres(host: String, port: Int) extends Backend
  final case class Sqlite(path: String) extends Backend
  object Backend {
    implicit val config: PureConfig = PureConfig.default.withDiscriminator("backend")
    implicit val reader: ConfigReader[Backend] = KindlingsConfigReader.derive[Backend]
  }

  final case class DatabaseConfig(
    @configKey("jdbc-url") jdbcUrl: String,
    @transientField cachedPoolName: Option[String] = None
  )
  object DatabaseConfig {
    implicit val reader: ConfigReader[DatabaseConfig] = KindlingsConfigReader.derive[DatabaseConfig]
    implicit val writer: ConfigWriter[DatabaseConfig] = KindlingsConfigWriter.derive[DatabaseConfig]
  }

  def verify(): Unit = {
    val server = ConfigSource.string("""
      host = "localhost"
    """).load[ServerConfig]
    assert(server.contains(ServerConfig("localhost", 8080)))

    val backend = ConfigSource.string("""
      backend = "postgres"
      host = "db.internal"
      port = 5432
    """).load[Backend]
    assert(backend.contains(Postgres("db.internal", 5432)))

    val database = ConfigSource.string("""
      jdbc-url = "jdbc:postgresql://localhost/app"
    """).load[DatabaseConfig]
    assert(database.contains(DatabaseConfig("jdbc:postgresql://localhost/app")))

    val written = ConfigWriter[DatabaseConfig].to(DatabaseConfig("jdbc:h2:mem:test", Some("private")))
    assert(!written.render().contains("cachedPoolName"))
  }
}

@main def runKindlingsDerivationExamples(): Unit = {
  CirceExamples.verify()
  PureConfigExamples.verify()
  println("Kindlings derivation examples verified")
}
