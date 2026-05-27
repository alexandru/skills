#!/usr/bin/env -S scala shebang -q

//> using scala "3.3.7"
//> using options "-no-indent"
//> using dep "org.typelevel::cats-effect::3.7.0"

import cats.effect.*
import cats.data.EitherT
import scala.util.Random
import scala.concurrent.duration.*

case class MyError(message: String)

def sayHello(name: String): EitherT[IO, MyError, String] =
  EitherT {
    for {
      _ <- IO.sleep(1.second)
      r <- IO {
        val rnd = Random.nextInt()
        if (rnd % 2 == 0)
          Left(MyError(s"Boom $rnd!"))
        else
          Right(s"Hello, $name (#$rnd)")
      }
    } yield r
  }

object HelloWorld extends IOApp.Simple {
  val run: IO[Unit] =
    sayHello("World").value.flatMap {
      case Left(error) =>
        IO.println(s"Error: ${error.message}")
      case Right(value) =>
        IO.println(s"Success: $value")
    }
}
