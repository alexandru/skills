///usr/bin/env jbang "$0" "$@" ; exit $?

//JAVA 17+

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;

class VerifyExamples {
    public static void main(String[] args) throws Exception {
        Path work = Files.createTempDirectory("kotlin-java-library-examples-");
        try {
            Path libraryJar = work.resolve("library.jar");
            Path javaOut = work.resolve("java-classes");
            Files.createDirectories(javaOut);

            Path kotlinSource = work.resolve("LibraryApi.kt");
            Path javaSource = work.resolve("JavaClient.java");
            Files.writeString(kotlinSource, KOTLIN_SOURCE, StandardCharsets.UTF_8);
            Files.writeString(javaSource, JAVA_CLIENT, StandardCharsets.UTF_8);

            run(
                "kotlinc",
                "-jvm-target",
                "17",
                "-Xjsr305=strict",
                "-include-runtime",
                "-d",
                libraryJar.toString(),
                kotlinSource.toString()
            );
            run(
                "javac",
                "-cp",
                libraryJar.toString(),
                "-d",
                javaOut.toString(),
                javaSource.toString()
            );
            run(
                "java",
                "-cp",
                libraryJar + File.pathSeparator + javaOut,
                "JavaClient"
            );

            System.out.println("Kotlin Java library examples compiled and ran.");
        } finally {
            deleteRecursively(work);
        }
    }

    private static void run(String... command) throws IOException, InterruptedException {
        Process process = new ProcessBuilder(command)
            .redirectErrorStream(true)
            .start();
        String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        int exitCode = process.waitFor();
        if (exitCode != 0) {
            throw new IllegalStateException(
                "Command failed with exit code " + exitCode + ": " + String.join(" ", command) + "\n" + output
            );
        }
    }

    private static void deleteRecursively(Path root) throws IOException {
        if (!Files.exists(root)) {
            return;
        }
        try (var paths = Files.walk(root)) {
            paths.sorted(Comparator.reverseOrder()).forEach(path -> {
                try {
                    Files.delete(path);
                } catch (IOException e) {
                    throw new RuntimeException(e);
                }
            });
        }
    }

    private static final String KOTLIN_SOURCE = """
        @file:JvmName("LibraryApis")

        package com.example.library

        import java.io.IOException
        import java.nio.file.Files
        import java.nio.file.Path
        import java.util.Collections

        class Client @JvmOverloads constructor(
            val endpoint: String,
            val timeoutMillis: Long = 2_000,
            val retries: Int = 1,
        ) {
            fun describe(): String = "$endpoint:$timeoutMillis:$retries"
        }

        @JvmOverloads
        fun connect(host: String, port: Int = 443, secure: Boolean = true): String =
            "$host:$port?secure=$secure"

        class Ids private constructor() {
            companion object {
                const val DEFAULT_PREFIX: String = "usr"

                @JvmField
                val MAX_ID_LENGTH: Int = 36

                @JvmStatic
                @JvmOverloads
                fun newId(prefix: String = DEFAULT_PREFIX): String =
                    "$prefix-0001"
            }
        }

        fun interface NameFormatter {
            fun format(name: String): String
        }

        fun greeting(name: String, formatter: NameFormatter): String =
            formatter.format(name)

        @Throws(IOException::class)
        fun readFirstLine(path: Path): String =
            Files.readAllLines(path).firstOrNull() ?: ""

        fun readOnlyNames(names: List<String>): List<String> =
            Collections.unmodifiableList(names.toList())

        @JvmName("displayStrings")
        fun List<String>.display(): String = joinToString(",")

        @JvmName("displayInts")
        fun List<Int>.display(): String = joinToString(":")

        @JvmRecord
        data class UserId(val value: String)

        interface Base {
            val id: String
        }

        class Derived(override val id: String) : Base

        class Box<out T>(val value: T)

        fun baseId(box: Box<Base>): String = box.value.id

        fun exactBaseId(box: Box<@JvmSuppressWildcards Base>): String =
            box.value.id
        """;

    private static final String JAVA_CLIENT = """
        import com.example.library.Base;
        import com.example.library.Box;
        import com.example.library.Client;
        import com.example.library.Derived;
        import com.example.library.Ids;
        import com.example.library.LibraryApis;
        import com.example.library.UserId;
        import java.io.IOException;
        import java.nio.file.Files;
        import java.nio.file.Path;
        import java.util.List;

        public class JavaClient {
            public static void main(String[] args) throws Exception {
                Client defaultClient = new Client("https://api.example.com");
                Client customClient = new Client("https://api.example.com", 5_000L, 2);
                require(defaultClient.describe().equals("https://api.example.com:2000:1"));
                require(customClient.describe().equals("https://api.example.com:5000:2"));

                require(LibraryApis.connect("example.com").equals("example.com:443?secure=true"));
                require(LibraryApis.connect("example.com", 8443, false).equals("example.com:8443?secure=false"));

                require(Ids.DEFAULT_PREFIX.equals("usr"));
                require(Ids.MAX_ID_LENGTH == 36);
                require(Ids.newId().equals("usr-0001"));
                require(Ids.newId("admin").equals("admin-0001"));

                String greeting = LibraryApis.greeting("Ada", name -> "Hello, " + name);
                require(greeting.equals("Hello, Ada"));

                Path config = Files.createTempFile("config", ".txt");
                Files.writeString(config, "first\\nsecond\\n");
                try {
                    require(LibraryApis.readFirstLine(config).equals("first"));
                } catch (IOException e) {
                    throw new AssertionError(e);
                } finally {
                    Files.deleteIfExists(config);
                }

                List<String> names = LibraryApis.readOnlyNames(List.of("Ada", "Grace"));
                require(names.size() == 2);
                try {
                    names.add("Katherine");
                    throw new AssertionError("readOnlyNames should be unmodifiable");
                } catch (UnsupportedOperationException expected) {
                    // Expected.
                }

                require(LibraryApis.displayStrings(List.of("a", "b")).equals("a,b"));
                require(LibraryApis.displayInts(List.of(1, 2)).equals("1:2"));

                UserId userId = new UserId("u-1");
                require(userId.value().equals("u-1"));

                require(LibraryApis.baseId(new Box<Derived>(new Derived("d-1"))).equals("d-1"));
                require(LibraryApis.exactBaseId(new Box<Base>(new Derived("b-1"))).equals("b-1"));
            }

            private static void require(boolean condition) {
                if (!condition) {
                    throw new AssertionError();
                }
            }
        }
        """;
}
