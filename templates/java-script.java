///usr/bin/env jbang "$0" "$@" ; exit $?

//JAVA 17+
//DEPS org.jspecify:jspecify:1.0.0

import java.util.Optional;
import org.jspecify.annotations.NullMarked;
import org.jspecify.annotations.Nullable;

@NullMarked
class JavaScriptTemplate {
  static @Nullable String emptyToNull(String value) {
    return value.isEmpty() ? null : value;
  }

  static Optional<String> firstNonEmpty(String first, String second) {
    return first.isEmpty() ? Optional.of(second) : Optional.of(first);
  }

  public static void main(String... args) {
    String value = args.length == 0 ? "" : args[0];
    System.out.println(firstNonEmpty(value, "fallback").orElseThrow());
  }
}
