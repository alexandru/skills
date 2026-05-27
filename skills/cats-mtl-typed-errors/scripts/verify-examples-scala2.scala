#!/usr/bin/env -S scala shebang -q

//> using scala "2.13.16"
//> using options "-Wnonunit-statement"
//> using dep "org.typelevel::cats-effect::3.7.0"
//> using dep "org.typelevel::cats-mtl::1.6.0"

import cats.Applicative
import cats.effect.{IO, IOApp}
import cats.mtl.{Handle, Raise}
import cats.mtl.syntax.all._
import cats.syntax.all._

object Scala2Sample {
  final case class Result(value: String)

  sealed trait ParseError extends Product with Serializable
  object ParseError {
    case object BlankInput extends ParseError
    final case class MissingSemicolon(input: String) extends ParseError
  }

  def parse[F[_]](input: String)(implicit r: Raise[F, ParseError], a: Applicative[F]): F[Result] = {
    val trimmed = input.trim
    if (trimmed.isEmpty)
      ParseError.BlankInput.raise[F, Result]
    else if (!trimmed.endsWith(";"))
      ParseError.MissingSemicolon(input).raise[F, Result]
    else
      Result(trimmed.dropRight(1)).pure[F]
  }

  val program: IO[String] =
    Handle.allowF[IO, ParseError] { implicit h =>
      parse[IO]("ok;").map(result => s"parsed ${result.value}")
    } rescue {
      case ParseError.BlankInput =>
        IO.pure("empty input")
      case ParseError.MissingSemicolon(text) =>
        IO.pure(s"missing semicolon in $text")
    }
}

object CatsMtlTypedErrorsScala2Examples extends IOApp.Simple {
  val run: IO[Unit] =
    Scala2Sample.program.void
}
