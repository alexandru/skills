///usr/bin/env jbang "$0" "$@" ; exit $?

//JAVA 17+
//DEPS org.jspecify:jspecify:1.0.0

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import org.jspecify.annotations.NonNull;
import org.jspecify.annotations.NullMarked;
import org.jspecify.annotations.NullUnmarked;
import org.jspecify.annotations.Nullable;

@NullMarked
class VerifyExamples {
  public static void main(String... args) {
    assertNull(Strings.emptyToNull(""));
    assertEquals("abc", Strings.emptyToNull("abc"));
    assertEquals("", Strings.nullToEmpty(null));

    TypeUseExamples typeUseExamples = new TypeUseExamples();
    List<@Nullable String> names = new ArrayList<>();
    names.add(null);
    names.add("JSpecify");
    typeUseExamples.acceptNames(names);

    SimpleBox<@Nullable String> nullableBox = new SimpleBox<>(null);
    nullableBox.set("ready");
    assertEquals("ready", nullableBox.get());

    StrictBox<String> strictBox = new ImmutableBox<>("value");
    assertEquals("value", strictBox.get());

    assertNull(First.firstOrNull(List.of()));
    assertEquals("fallback", First.firstOrDefault(List.of(), "fallback"));
    List<@Nullable String> maybeNames = new ArrayList<>();
    maybeNames.add(null);
    maybeNames.add("x");
    assertEquals(Optional.of("x"), First.firstPresent(maybeNames));

    LegacyBoundary legacyBoundary = new LegacyBoundary();
    assertNull(legacyBoundary.legacyEcho(null));
  }

  static void assertNull(@Nullable Object value) {
    if (value != null) {
      throw new AssertionError("Expected null, got " + value);
    }
  }

  static void assertEquals(@Nullable Object expected, @Nullable Object actual) {
    if (!Objects.equals(expected, actual)) {
      throw new AssertionError("Expected " + expected + ", got " + actual);
    }
  }
}

@NullMarked
final class Strings {
  static @Nullable String emptyToNull(String value) {
    return value.isEmpty() ? null : value;
  }

  static String nullToEmpty(@Nullable String value) {
    return value == null ? "" : value;
  }
}

@NullMarked
final class TypeUseExamples {
  @Nullable String[] nullableElements = {null, "name"};
  String @Nullable [] nullableArray = null;
  @Nullable String @Nullable [] nullableArrayAndElements = null;
  Map.@Nullable Entry<String, String> nullableEntry = null;

  void acceptNames(List<@Nullable String> names) {
    List<@Nullable String> copy = new ArrayList<>(names);
    copy.add(null);
  }
}

@NullMarked
interface Box<T extends @Nullable Object> {
  T get();

  void set(T value);
}

@NullMarked
final class SimpleBox<T extends @Nullable Object> implements Box<T> {
  private T value;

  SimpleBox(T value) {
    this.value = value;
  }

  @Override
  public T get() {
    return value;
  }

  @Override
  public void set(T value) {
    this.value = value;
  }
}

@NullMarked
interface StrictBox<T> {
  T get();
}

@NullMarked
final class ImmutableBox<T> implements StrictBox<T> {
  private final T value;

  ImmutableBox(T value) {
    this.value = value;
  }

  @Override
  public T get() {
    return value;
  }
}

@NullMarked
final class First {
  static <T> @Nullable T firstOrNull(List<T> values) {
    return values.isEmpty() ? null : values.get(0);
  }

  static <T extends @Nullable Object> T firstOrDefault(List<T> values, T defaultValue) {
    return values.isEmpty() ? defaultValue : values.get(0);
  }

  static <T extends @Nullable Object> Optional<@NonNull T> firstPresent(List<T> values) {
    for (T value : values) {
      if (value != null) {
        return Optional.of(value);
      }
    }
    return Optional.empty();
  }
}

@NullMarked
final class LegacyBoundary {
  @NullUnmarked
  @Nullable Object legacyEcho(@Nullable Object value) {
    return value;
  }
}
