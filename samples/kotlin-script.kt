///usr/bin/env jbang "$0" "$@" ; exit $?

//JAVA 17+
//KOTLIN 2.3.21
//COMPILE_OPTIONS -Xcontext-parameters
//DEPS io.arrow-kt:arrow-core:2.2.2.1
//DEPS org.jetbrains.kotlinx:kotlinx-coroutines-core:1.11.0

import arrow.core.Either
import arrow.core.raise.context.either
import arrow.core.raise.context.raise
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import kotlin.random.Random
import kotlin.time.Duration.Companion.seconds

data class MyError(val message: String)

suspend fun sayHello(name: String): Either<MyError, String> =
    either {
        withContext(Dispatchers.Default) {
            delay(1.seconds)
            val rnd = Random.nextInt()
            if (rnd % 2 == 0)
                raise(MyError("Boom ${rnd}!"))
            "Hello, $name (#$rnd)"
        }
    }

fun main(vararg args: String) = runBlocking {
    when (val r = sayHello(args.firstOrNull() ?: "World")) {
        is Either.Left -> println("Error: ${r.value.message}")
        is Either.Right -> println("Success: ${r.value}")
    }
}
