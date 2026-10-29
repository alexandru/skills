#!/usr/bin/env -S scala shebang -q

//> using scala "3.3.7"
//> using options "-no-indent" "-Wnonunit-statement"
//> using dep "org.typelevel::cats-effect::3.7.0"

import cats.effect.*
import cats.syntax.all.*

import java.io.{BufferedReader, FileInputStream}
import java.nio.file.{Files, Path}

def bufferedReader[F[_]: Sync](path: Path): Resource[F, BufferedReader] =
  Resource.fromAutoCloseable(Sync[F].blocking(Files.newBufferedReader(path)))

def leakedClosedReader(path: Path): IO[BufferedReader] =
  bufferedReader[IO](path).use(IO.pure)

def firstLine(path: Path): IO[Option[String]] =
  bufferedReader[IO](path).use { reader =>
    IO.interruptible(Option(reader.readLine()))
  }

final class UserProcessor private () {
  private var running: Boolean = false

  private def start(): Unit =
    running = true

  private def shutdown(): Unit =
    running = false

  def process[F[_]: Sync](line: String): F[String] =
    Sync[F].delay {
      if (!running) throw new IllegalStateException("processor is shut down")
      line.trim.toUpperCase
    }
}

object UserProcessor {
  def resource[F[_]: Sync]: Resource[F, UserProcessor] =
    Resource.make {
      Sync[F].delay {
        val processor = new UserProcessor
        processor.start()
        processor
      }
    } { processor =>
      Sync[F].delay(processor.shutdown())
    }
}

final class ReportService[F[_]: Sync] private (
    processor: UserProcessor,
    reader: BufferedReader
) {
  def firstProcessedLine: F[Option[String]] =
    Sync[F].interruptible(reader.readLine()).flatMap {
      case null => Sync[F].pure(None)
      case line => processor.process[F](line).map(Some(_))
    }
}

object ReportService {
  private def reportReader[F[_]: Sync](path: Path): Resource[F, BufferedReader] =
    Resource.fromAutoCloseable(Sync[F].blocking(Files.newBufferedReader(path)))

  def resource[F[_]: Sync](path: Path): Resource[F, ReportService[F]] =
    (UserProcessor.resource[F], reportReader[F](path)).mapN { (processor, reader) =>
      new ReportService[F](processor, reader)
    }
}

def runReport(path: Path): IO[Option[String]] =
  ReportService.resource[IO](path).use(_.firstProcessedLine)

final class Handle(id: String) {
  def close(): Unit = ()
}

def acquireOne[F[_]: Sync](id: String): Resource[F, Handle] =
  Resource.make(Sync[F].delay(new Handle(id)))(handle =>
    Sync[F].delay(handle.close())
  )

def acquireAll[F[_]: Sync](ids: List[String]): Resource[F, List[Handle]] =
  ids.traverse(acquireOne[F])

def auditScope[F[_]: Sync](events: Ref[F, List[String]]): Resource[F, Unit] =
  Resource.makeCase(Sync[F].unit) { (_, exitCase) =>
    events.update(exitCase.toString :: _)
  }

def fileInputStreamResource[F[_]: Sync](path: Path): Resource[F, FileInputStream] =
  Resource.fromAutoCloseable(Sync[F].blocking(new FileInputStream(path.toFile)))

def readFirstByteViaResource(path: Path): IO[Int] =
  fileInputStreamResource[IO](path).use(stream => IO.interruptible(stream.read()))

def allocatedSafely(path: Path): IO[Option[String]] =
  ReportService.resource[IO](path).allocated.flatMap { case (service, release) =>
    service.firstProcessedLine.guarantee(release)
  }

def tempFile: Resource[IO, Path] =
  Resource.make(IO.blocking(Files.createTempFile("cats-effect-resource", ".txt"))) { path =>
    IO.blocking(Files.deleteIfExists(path)).void
  }

def writeSample(path: Path): IO[Unit] =
  IO.blocking(Files.writeString(path, "alpha\nbeta\n")).void

object CatsEffectResourceExamples extends IOApp.Simple {
  val run: IO[Unit] =
    tempFile.use { path =>
      for {
        _ <- writeSample(path)
        _ <- firstLine(path)
        _ <- runReport(path)
        _ <- allocatedSafely(path)
        _ <- acquireAll[IO](List("one", "two")).use_.void
      } yield ()
    }
}
