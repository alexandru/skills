#!/usr/bin/env -S scala shebang -q

//> using scala "3.3.7"
//> using options "-Wnonunit-statement"
//> using dep "org.typelevel::cats-effect::3.7.0"
//> using dep "org.typelevel::cats-mtl::1.6.0"

import cats.{Applicative, Monad}
import cats.effect.{IO, IOApp}
import cats.mtl.{Handle, Raise}
import cats.mtl.syntax.all.*
import cats.syntax.all.*

final case class Result(value: String)

enum ParseError:
  case BlankInput
  case MissingSemicolon(input: String)

def parse[F[_]](input: String)(using Raise[F, ParseError], Applicative[F]): F[Result] =
  val trimmed = input.trim
  if trimmed.isEmpty then
    ParseError.BlankInput.raise[F, Result]
  else if !trimmed.endsWith(";") then
    ParseError.MissingSemicolon(input).raise
  else
    Result(trimmed.dropRight(1)).pure[F]

type ParseEither[A] = Either[ParseError, A]

def parseEither(input: String): Either[ParseError, Result] =
  parse[ParseEither](input)

def parseIoOnly(input: String)(using Raise[IO, ParseError]): IO[Result] =
  parse[IO](input)

def parseOrFallback[F[_]](input: String)(using Handle[F, ParseError], Applicative[F]): F[Result] =
  parse[F](input).handle[ParseError] {
    case ParseError.BlankInput             => Result("default")
    case ParseError.MissingSemicolon(text) => Result(text.trim)
  }

def parseProgram(input: String): IO[String] =
  Handle.allow[ParseError]:
    parseIoOnly(input).map(result => s"parsed ${result.value}")
  .rescue:
    case ParseError.BlankInput =>
      IO.pure("empty input")
    case ParseError.MissingSemicolon(text) =>
      IO.pure(s"missing semicolon in $text")

enum AppError:
  case Parse(error: ParseError)
  case MissingConfig(key: String)

def loadConfig[F[_]](key: String)(using Raise[F, AppError], Applicative[F]): F[String] =
  if key == "script" then "println;".pure[F]
  else AppError.MissingConfig(key).raise

def parseConfigured[F[_]](key: String)(using Raise[F, AppError], Monad[F]): F[Result] =
  loadConfig[F](key).flatMap { source =>
    parseEither(source).fold(
      error => AppError.Parse(error).raise[F, Result],
      result => result.pure[F]
    )
  }

def appProgram(key: String): IO[String] =
  Handle.allow[AppError]:
    parseConfigured[IO](key).map(_.value)
  .rescue:
    case AppError.Parse(ParseError.BlankInput) =>
      IO.pure("configured script was blank")
    case AppError.Parse(ParseError.MissingSemicolon(_)) =>
      IO.pure("configured script was incomplete")
    case AppError.MissingConfig(missingKey) =>
      IO.pure(s"missing config: $missingKey")

object CatsMtlTypedErrorsExamples extends IOApp.Simple:
  val run: IO[Unit] =
    for
      _ <- IO.fromEither(parseEither("ok;").leftMap(error => new RuntimeException(error.toString)))
      _ <- parseProgram("ok;")
      _ <- parseProgram("missing")
      _ <- Handle.allow[ParseError](parseOrFallback[IO]("").void).rescue(_ => IO.unit)
      _ <- appProgram("script")
      _ <- appProgram("missing")
    yield ()
