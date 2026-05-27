#!/usr/bin/env -S scala shebang -q

//> using scala "3.3.7"
//> using options "-no-indent" "-Wnonunit-statement"
//> using dep "org.typelevel::cats-effect::3.7.0"
//> using dep "org.typelevel::cats-effect-testkit::3.7.0"

import cats.effect.*
import cats.effect.std.{Dispatcher, Random}
import cats.effect.testkit.TestControl
import cats.syntax.all.*

import java.io.FileInputStream
import java.nio.file.Path
import java.time.Instant
import scala.concurrent.Future
import scala.concurrent.duration.*

def nowIO: IO[Instant] =
  IO(Instant.now())

def nowF[F[_]: Sync]: F[Instant] =
  Sync[F].delay(Instant.now())

def clockNow[F[_]: Clock]: F[Instant] =
  Clock[F].realTimeInstant

def randomInt[F[_]: Sync]: F[Int] =
  Random.scalaUtilRandom[F].flatMap(_.nextInt)

def readEnv[F[_]: Sync](key: String): F[Option[String]] =
  Sync[F].delay(sys.env.get(key))

final class Scratch private (private val buffer: Array[Byte]) {
  def size: Int = buffer.length
}

object Scratch {
  def create[F[_]: Sync](size: Int): F[Scratch] =
    Sync[F].delay(new Scratch(new Array[Byte](size)))
}

final class Counter private (ref: Ref[IO, Int]) {
  def next: IO[Int] =
    ref.updateAndGet(_ + 1)
}

object Counter {
  def create: IO[Counter] =
    Ref.of[IO, Int](0).map(new Counter(_))
}

def inputStream(path: Path): Resource[IO, FileInputStream] =
  Resource.fromAutoCloseable(IO.blocking(new FileInputStream(path.toFile)))

def readFirstByte(path: Path): IO[Int] =
  inputStream(path).use(in => IO.interruptible(in.read()))

def interruptibleSleep[F[_]: Sync]: F[Unit] =
  Sync[F].interruptible(Thread.sleep(250))

def fromOutcome[A](outcome: Outcome[IO, Throwable, A]): IO[A] =
  outcome match {
    case Outcome.Succeeded(fa) => fa
    case Outcome.Errored(e)    => IO.raiseError(e)
    case Outcome.Canceled()    => IO.canceled *> IO.never[A]
  }

def startAndJoin[A](ioa: IO[A]): IO[A] =
  ioa.start.flatMap(_.join).flatMap(fromOutcome)

def timeoutToOption[A](ioa: IO[A], limit: FiniteDuration): IO[Option[A]] =
  IO.race(ioa, IO.sleep(limit)).map {
    case Left(value) => Some(value)
    case Right(_)    => None
  }

def fastest[A](left: IO[A], right: IO[A]): IO[A] =
  IO.racePair(left, right).flatMap {
    case Left((winner, loser))  => loser.cancel *> fromOutcome(winner)
    case Right((loser, winner)) => loser.cancel *> fromOutcome(winner)
  }

def parallelPrint: IO[Unit] =
  (IO.println("A"), IO.println("B")).parTupled.void

def toFutureCallback(using dispatcher: Dispatcher[IO]): String => Future[Unit] =
  message => dispatcher.unsafeToFuture(IO.println(message))

val syncValue: SyncIO[Int] =
  SyncIO(1)

val liftedValue: IO[Int] =
  syncValue.to[IO]

def virtualTimeResult: IO[Int] =
  TestControl.executeEmbed(IO.sleep(1.second) *> IO.pure(42))

object CatsEffectIoExamples extends IOApp.Simple {
  val run: IO[Unit] =
    for {
      _ <- nowIO
      _ <- randomInt[IO]
      _ <- Scratch.create[IO](1024)
      _ <- Counter.create.flatMap(_.next)
      _ <- timeoutToOption(IO.pure(42), 1.second)
      _ <- startAndJoin(IO.pure(1))
      _ <- fastest(IO.pure("left"), IO.sleep(10.millis).as("right"))
      _ <- virtualTimeResult
    } yield ()
}
