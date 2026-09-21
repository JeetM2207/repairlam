"""Curated, individually-verified real-world bug specs for live_bug_pipeline.
Each entry's regression test is built directly from the actual issue text
(and, where relevant, maintainer comments confirming both the bug and the
intended fix direction) -- never guessed from a title alone. Candidates
where a maintainer disputed whether there even *is* a well-defined fix
(e.g. gson#2816, where the maintainer's own reply says the "correct"
exception type is genuinely unsettled) were deliberately excluded: an
FSM run against an ill-posed bug can't be fairly scored PLAUSIBLE/
ESCALATED/TIMEOUT.
"""
from repairlam.github.live_bug_pipeline import BugSpec

MAVEN_NO_FAIL_IF_NO_TESTS = "-Dsurefire.failIfNoSpecifiedTests=false"

SPECS = [
    BugSpec(
        key="guava#5284",
        source_repo="google/guava",
        source_issue_number=5284,
        base_branch="master",
        test_file="guava-tests/test/com/google/common/io/BaseEncodingTest.java",
        # anchor: end of testToString(), the last method in the class, just
        # before the class's closing brace -- verified against the live
        # file content, occurs exactly once.
        test_insert_after=(
            "    assertThat(base16().withSeparator(\"\\n\", 10).toString())\n"
            "        .isEqualTo(\"BaseEncoding.base16().withSeparator(\\\"\\n\\\", 10)\");\n"
            "  }"
        ),
        test_method=(
            "  // https://github.com/google/guava/issues/5284: Closeable.close() must have no\n"
            "  // effect if the stream is already closed (maintainer-agreed: track a closed flag\n"
            "  // and reset bitBufferLength on first close), but a second close() on an\n"
            "  // encodingStream() writer was still flushing a stale buffered byte, corrupting\n"
            "  // output already read by the caller.\n"
            "  public void testEncodingStreamCloseIsIdempotent() throws IOException {\n"
            "    StringWriter w = new StringWriter();\n"
            "    OutputStream out = base64().encodingStream(w);\n"
            "    out.write(0);\n"
            "    out.close();\n"
            "    String afterFirstClose = w.toString();\n"
            "    out.close();\n"
            "    assertThat(w.toString()).isEqualTo(afterFirstClose);\n"
            "  }"
        ),
        test_cmd=["mvn", "-q", "-pl", "guava-tests", "-am", "-Dtest=BaseEncodingTest",
                  MAVEN_NO_FAIL_IF_NO_TESTS, "test"],
    ),
    BugSpec(
        key="gson#2680",
        source_repo="google/gson",
        source_issue_number=2680,
        base_branch="main",
        test_file="gson/src/test/java/com/google/gson/functional/JsonTreeTest.java",
        # anchor: `private Gson gson;` field declaration right after the class
        # opening -- occurs exactly once, right after @Before setUp() usually
        # follows; inserting a new @Test method right after it is safe.
        test_insert_after="public class JsonTreeTest {\n  private Gson gson;",
        test_method=(
            "\n\n"
            "  // https://github.com/google/gson/issues/2680: toJsonTree() on an Integer\n"
            "  // silently widened it to a Long (maintainer-confirmed regression from commit\n"
            "  // 3e3266cf, which routed all integral adapters through JsonWriter.value(long)).\n"
            "  // Expected: the resulting JsonPrimitive's number stays an Integer.\n"
            "  @Test\n"
            "  public void testToJsonTreeKeepsIntegerType() {\n"
            "    Integer testNum = 1;\n"
            "    JsonElement jsonTree = new Gson().toJsonTree(testNum);\n"
            "    assertThat(jsonTree.getAsNumber()).isInstanceOf(Integer.class);\n"
            "  }"
        ),
        test_cmd=["mvn", "-q", "-pl", "gson", "-am", "-Dtest=JsonTreeTest",
                  MAVEN_NO_FAIL_IF_NO_TESTS, "test"],
    ),
    BugSpec(
        key="jackson-databind#3067",
        source_repo="FasterXML/jackson-databind",
        source_issue_number=3067,
        base_branch="3.x",
        test_file="src/test/java/tools/jackson/databind/deser/filter/JsonIgnorePropertiesDeserTest.java",
        # anchor: end of the file's last helper class (AnySetter5865Pojo),
        # right before the outer class's closing brace -- occurs exactly once.
        test_insert_after=(
            "        @JsonAnySetter\n"
            "        public void setOther(String key, Object value) {\n"
            "            other.put(key, value);\n"
            "        }\n"
            "    }"
        ),
        test_method=(
            "\n"
            "    // https://github.com/FasterXML/jackson-databind/issues/3067:\n"
            "    // @JsonIgnoreProperties(ignoreUnknown = false) on a class should take\n"
            "    // precedence over a lenient DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES=false\n"
            "    // configured on the mapper and still reject unknown properties -- but the\n"
            "    // annotation's ignoreUnknown=false was silently ignored whenever the mapper-level\n"
            "    // feature was off.\n"
            "    @JsonIgnoreProperties(ignoreUnknown = false)\n"
            "    static class Strict3067Pojo {\n"
            "        public String name;\n"
            "    }\n"
            "\n"
            "    @Test\n"
            "    public void testIgnorePropertiesFalseOverridesLenientMapper3067() throws Exception\n"
            "    {\n"
            "        final ObjectMapper lenientMapper = jsonMapperBuilder()\n"
            "                .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)\n"
            "                .build();\n"
            "        final String json = a2q(\"{'name':'test','extra':'value'}\");\n"
            "        assertThrows(UnrecognizedPropertyException.class, () ->\n"
            "                lenientMapper.readValue(json, Strict3067Pojo.class));\n"
            "    }"
        ),
        test_cmd=["mvn", "-q", "-Dtest=JsonIgnorePropertiesDeserTest",
                  MAVEN_NO_FAIL_IF_NO_TESTS, "test"],
    ),
]


def _gson_cmd(klass):
    return ["mvn", "-q", "-pl", "gson", "-am", f"-Dtest={klass}",
            MAVEN_NO_FAIL_IF_NO_TESTS, "test"]


def _guava_cmd(klass):
    return ["mvn", "-q", "-pl", "guava-tests", "-am", f"-Dtest={klass}",
            MAVEN_NO_FAIL_IF_NO_TESTS, "test"]


# Second batch: curated with a faster per-candidate filter (open + bug/defect
# label + a clear repro or fix proposal in the body/comments + single-method
# scope), rather than the deep maintainer-thread read used for the first
# batch. Every regression test below is still built directly from the
# issue's own repro code/values (mechanically transcribed, not invented) and
# every candidate whose "fix" turned out to be genuinely disputed or
# unresolved among maintainers (checked via a quick comments fetch) was
# dropped rather than kept for throughput's sake -- e.g. guava#1898 and
# guava#6226, where maintainers openly disagreed on the correct semantics;
# gson#1907/#1778/#1437, where the issue itself has no solid, environment-
# independent repro. square/okhttp and square/retrofit were skipped entirely
# after their GitHub redirects revealed the repos changed owners (now under
# an unfamiliar org) since this session's prior knowledge of them.
SPECS += [
    BugSpec(
        key="guava#1065",
        source_repo="google/guava",
        source_issue_number=1065,
        base_branch="master",
        new_test_file="guava-tests/test/com/google/common/net/InternetDomainNameHyphen1065Test.java",
        new_test_file_content="""\
package com.google.common.net;

import static com.google.common.truth.Truth.assertThat;

import org.junit.Test;

// https://github.com/google/guava/issues/1065: InternetDomainName.from() rejected a
// subdomain label ending in a hyphen (e.g. "vilnius-"), even though that's a valid
// registrable label; the real-world domain in the issue resolves (HTTP 200) despite
// Guava refusing to parse it.
public class InternetDomainNameHyphen1065Test {
  @Test
  public void testTrailingHyphenInSubdomainIsAccepted() {
    InternetDomainName name = InternetDomainName.from("www.vilnius-.hotelreservierung.de");
    assertThat(name.parts()).containsExactly("www", "vilnius-", "hotelreservierung", "de")
        .inOrder();
  }
}
""",
        test_cmd=_guava_cmd("InternetDomainNameHyphen1065Test"),
    ),
    BugSpec(
        key="guava#3790",
        source_repo="google/guava",
        source_issue_number=3790,
        base_branch="master",
        new_test_file="guava-tests/test/com/google/common/collect/PartitionRemoveAll3790Test.java",
        new_test_file_content="""\
package com.google.common.collect;

import static com.google.common.truth.Truth.assertThat;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.junit.Test;

// https://github.com/google/guava/issues/3790: iterating Lists.partition(list, n)'s
// sublists and calling removeAll() on each throws NoSuchElementException, because
// emptying a partition sublist removes it from the parent partitioned view, which
// invalidates the outer iteration Lists.partition() is currently in the middle of.
public class PartitionRemoveAll3790Test {
  @Test
  public void testRemoveAllOnPartitionedSublistsDoesNotThrow() {
    List<Integer> source = new ArrayList<>(Arrays.asList(1, 2, 3, 4));
    List<List<Integer>> partitions = Lists.partition(source, 2);
    for (List<Integer> partition : partitions) {
      partition.removeAll(Arrays.asList(1, 2, 3, 4));
    }
    assertThat(source).isEmpty();
  }
}
""",
        test_cmd=_guava_cmd("PartitionRemoveAll3790Test"),
    ),
    BugSpec(
        key="guava#3768",
        source_repo="google/guava",
        source_issue_number=3768,
        base_branch="master",
        new_test_file="guava-tests/test/com/google/common/collect/ObjectArraysConcatArrayStore3768Test.java",
        new_test_file_content="""\
package com.google.common.collect;

import static org.junit.Assert.assertArrayEquals;

import org.junit.Test;

// https://github.com/google/guava/issues/3768: ObjectArrays.concat(T[], T) infers the
// result's component type from the array argument, so concat(new String[0], (Object) 0)
// creates a String[]-backed array and then throws ArrayStoreException trying to store an
// Integer into it, instead of returning a plain Object[] like the sibling
// concat(T, T[]) overload's Class<T>-based version does correctly.
public class ObjectArraysConcatArrayStore3768Test {
  @Test
  public void testConcatSingleElementDoesNotThrowArrayStoreException() {
    String[] array = new String[0];
    Object[] concatenated = ObjectArrays.concat(array, (Object) 0);
    assertArrayEquals(new Object[] {0}, concatenated);
  }
}
""",
        test_cmd=_guava_cmd("ObjectArraysConcatArrayStore3768Test"),
    ),
    BugSpec(
        key="gson#2348",
        source_repo="google/gson",
        source_issue_number=2348,
        base_branch="main",
        new_test_file="gson/src/test/java/com/google/gson/functional/ExclusionStrategyFieldConflict2348Test.java",
        new_test_file_content="""\
package com.google.gson.functional;

import static org.junit.Assert.assertEquals;

import com.google.gson.ExclusionStrategy;
import com.google.gson.FieldAttributes;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.annotations.SerializedName;
import org.junit.Test;

// https://github.com/google/gson/issues/2348: a deserialization-only ExclusionStrategy
// that skips a superclass field sharing a serialized name with a subclass field is
// ignored, because Gson's own conflict check only skips a field when BOTH serialize and
// deserialize are excluded (AND) instead of either (OR) -- so the "excluded" superclass
// field still collides with the subclass field and fromJson() throws.
public class ExclusionStrategyFieldConflict2348Test {
  public static class BaseClass {
    @SerializedName("data")
    private Object data = null;
  }

  public static class SpecificClass extends BaseClass {
    @SerializedName("data")
    private String concreteData = null;
  }

  @Test
  public void testDeserializationExclusionStrategyAvoidsFieldConflict() {
    GsonBuilder builder = new GsonBuilder();
    builder.addDeserializationExclusionStrategy(new ExclusionStrategy() {
      @Override
      public boolean shouldSkipField(FieldAttributes f) {
        return "data".equals(f.getName()) && Object.class.equals(f.getDeclaringClass());
      }

      @Override
      public boolean shouldSkipClass(Class<?> clazz) {
        return false;
      }
    });
    Gson gson = builder.create();
    SpecificClass result = gson.fromJson("{\\"data\\":\\"Test String\\"}", SpecificClass.class);
    assertEquals("Test String", result.concreteData);
  }
}
""",
        test_cmd=_gson_cmd("ExclusionStrategyFieldConflict2348Test"),
    ),
    BugSpec(
        key="gson#2190",
        source_repo="google/gson",
        source_issue_number=2190,
        base_branch="main",
        new_test_file="gson/src/test/java/com/google/gson/functional/ExclusionStrategyAffectsSerialization2190Test.java",
        new_test_file_content="""\
package com.google.gson.functional;

import static org.junit.Assert.assertEquals;

import com.google.gson.ExclusionStrategy;
import com.google.gson.FieldAttributes;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.TypeAdapter;
import com.google.gson.stream.JsonReader;
import com.google.gson.stream.JsonWriter;
import java.io.IOException;
import org.junit.Test;

// https://github.com/google/gson/issues/2190: registering a *de*serialization-only
// ExclusionStrategy changes *serialized* output too, because
// TypeAdapterRuntimeTypeWrapper mistakes the Excluder-wrapped reflective adapter for a
// non-reflective one and picks the wrong adapter on write().
public class ExclusionStrategyAffectsSerialization2190Test {
  static class Base {}

  static class Sub extends Base {
    int i = 0;
  }

  static class Container {
    Base b = new Sub();
  }

  @Test
  public void testDeserializationExclusionStrategyDoesNotAffectSerialization() {
    ExclusionStrategy exclusionStrategy = new ExclusionStrategy() {
      @Override
      public boolean shouldSkipField(FieldAttributes f) {
        return false;
      }

      @Override
      public boolean shouldSkipClass(Class<?> clazz) {
        return clazz == Sub.class;
      }
    };

    Gson gson = new GsonBuilder()
        .registerTypeAdapter(Base.class, new TypeAdapter<Base>() {
          @Override
          public Base read(JsonReader in) throws IOException {
            throw new AssertionError("not needed");
          }

          @Override
          public void write(JsonWriter out, Base value) throws IOException {
            out.value("custom-adapter");
          }
        })
        .addDeserializationExclusionStrategy(exclusionStrategy)
        .create();

    assertEquals("{\\"b\\":\\"custom-adapter\\"}", gson.toJson(new Container()));
  }
}
""",
        test_cmd=_gson_cmd("ExclusionStrategyAffectsSerialization2190Test"),
    ),
    BugSpec(
        key="gson#1994",
        source_repo="google/gson",
        source_issue_number=1994,
        base_branch="main",
        new_test_file="gson/src/test/java/com/google/gson/functional/IntOverflowFromJsonObject1994Test.java",
        new_test_file_content="""\
package com.google.gson.functional;

import static org.junit.Assert.assertThrows;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import org.junit.Test;

// https://github.com/google/gson/issues/1994: fromJson(String, Class) throws when a JSON
// long value overflows an int field, but fromJson(JsonObject, Class) on the exact same
// oversized value silently truncates (integer overflow) instead of throwing -- the two
// entry points should behave consistently.
public class IntOverflowFromJsonObject1994Test {
  public static class HasIntField {
    public int foo;
  }

  @Test
  public void testFromJsonObjectRejectsLongOverflowingInt() {
    JsonObject jsonObject = new JsonObject();
    jsonObject.addProperty("foo", 10000000000L);
    assertThrows(RuntimeException.class, () -> new Gson().fromJson(jsonObject, HasIntField.class));
  }
}
""",
        test_cmd=_gson_cmd("IntOverflowFromJsonObject1994Test"),
    ),
    BugSpec(
        key="gson#1736",
        source_repo="google/gson",
        source_issue_number=1736,
        base_branch="main",
        new_test_file="gson/src/test/java/com/google/gson/functional/JsonWriterNaNWritesName1736Test.java",
        new_test_file_content="""\
package com.google.gson.functional;

import static org.junit.Assert.assertEquals;

import com.google.gson.stream.JsonWriter;
import java.io.IOException;
import java.io.StringWriter;
import org.junit.Test;

// https://github.com/google/gson/issues/1736: a non-lenient JsonWriter.value(double) for
// NaN/Infinity writes the pending property *name* before checking the value is valid and
// throwing -- so with setSerializeNulls(false), the name is left dangling with no value
// ever written for it, corrupting subsequent output.
public class JsonWriterNaNWritesName1736Test {
  @Test
  public void testNonLenientValueDoesNotWriteNameBeforeThrowing() throws IOException {
    StringWriter stringWriter = new StringWriter();
    JsonWriter jsonWriter = new JsonWriter(stringWriter);
    jsonWriter.setSerializeNulls(false);
    jsonWriter.beginObject();

    jsonWriter.name("test");
    try {
      jsonWriter.value(Double.NaN);
      throw new AssertionError("expected IllegalArgumentException");
    } catch (IllegalArgumentException expected) {
      // expected
    }
    jsonWriter.nullValue();

    jsonWriter.endObject();
    assertEquals("{}", stringWriter.toString());
  }
}
""",
        test_cmd=_gson_cmd("JsonWriterNaNWritesName1736Test"),
    ),
    BugSpec(
        key="gson#1735",
        source_repo="google/gson",
        source_issue_number=1735,
        base_branch="main",
        new_test_file="gson/src/test/java/com/google/gson/functional/JsonReaderPeekAdvances1735Test.java",
        new_test_file_content="""\
package com.google.gson.functional;

import com.google.gson.stream.JsonReader;
import com.google.gson.stream.MalformedJsonException;
import java.io.IOException;
import java.io.StringReader;
import org.junit.Test;

// https://github.com/google/gson/issues/1735: when JsonReader.peek() encounters malformed
// JSON and throws, it has already advanced the reader's internal position -- so retrying
// or continuing to read after catching the exception desyncs from the real character
// stream instead of leaving the reader's state untouched.
public class JsonReaderPeekAdvances1735Test {
  @Test
  public void testPeekDoesNotAdvanceReaderStateWhenThrowing() throws IOException {
    JsonReader reader = new JsonReader(new StringReader("[a?$,1]"));
    reader.beginArray();
    for (int i = 0; i < 4; i++) {
      try {
        reader.peek();
      } catch (MalformedJsonException expected) {
        // expected
      }
    }
    reader.nextInt();
    reader.endArray();
  }
}
""",
        test_cmd=_gson_cmd("JsonReaderPeekAdvances1735Test"),
    ),
    BugSpec(
        key="gson#1511",
        source_repo="google/gson",
        source_issue_number=1511,
        base_branch="main",
        new_test_file="gson/src/test/java/com/google/gson/internal/bind/util/Iso8601LocalTimezone1511Test.java",
        new_test_file_content="""\
package com.google.gson.internal.bind.util;

import static org.junit.Assert.assertEquals;

import java.text.ParsePosition;
import java.time.Instant;
import java.util.Date;
import java.util.TimeZone;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

// https://github.com/google/gson/issues/1511: ISO8601Utils.parse() on a date-only string
// ("yyyy-MM-dd", no time/timezone component) builds the Calendar with the JVM's default
// timezone instead of UTC, so the parsed instant shifts by the local UTC offset -- the
// same input parses to a different instant depending on the system's default timezone.
public class Iso8601LocalTimezone1511Test {
  private TimeZone originalDefault;

  @Before
  public void setUp() {
    originalDefault = TimeZone.getDefault();
    TimeZone.setDefault(TimeZone.getTimeZone("Europe/Paris"));
  }

  @After
  public void tearDown() {
    TimeZone.setDefault(originalDefault);
  }

  @Test
  public void testDateOnlyParseIsTimezoneIndependent() {
    Date parsed = ISO8601Utils.parse("2019-03-20", new ParsePosition(0));
    assertEquals(Instant.parse("2019-03-20T00:00:00Z"), parsed.toInstant());
  }
}
""",
        test_cmd=_gson_cmd("Iso8601LocalTimezone1511Test"),
    ),
    BugSpec(
        key="gson#1394",
        source_repo="google/gson",
        source_issue_number=1394,
        base_branch="main",
        new_test_file="gson/src/test/java/com/google/gson/functional/DeserializedMapValuesReserialize1394Test.java",
        new_test_file_content="""\
package com.google.gson.functional;

import static org.junit.Assert.assertEquals;

import com.google.gson.Gson;
import java.util.Map;
import org.junit.Test;

// https://github.com/google/gson/issues/1394: a Map deserialized by Gson (backed
// internally by LinkedTreeMap) can't have its own .values() view serialized again --
// unlike keySet() and entrySet(), LinkedTreeMap doesn't override values(), so it falls
// back to AbstractMap's anonymous-inner-class view, which Gson's reflective adapter
// excludes from serialization, producing "null" instead of the actual values.
public class DeserializedMapValuesReserialize1394Test {
  public static class Data {
    Map<String, String> map;
  }

  @Test
  public void testDeserializedMapValuesCanBeSerializedAgain() {
    Gson gson = new Gson();
    Data deserialized = gson.fromJson("{\\"map\\":{\\"key\\":\\"value\\"}}", Data.class);
    assertEquals("[\\"value\\"]", gson.toJson(deserialized.map.values()));
  }
}
""",
        test_cmd=_gson_cmd("DeserializedMapValuesReserialize1394Test"),
    ),
    BugSpec(
        key="gson#630",
        source_repo="google/gson",
        source_issue_number=630,
        base_branch="main",
        new_test_file="gson/src/test/java/com/google/gson/functional/JsonElementGetAsIntOverflow630Test.java",
        new_test_file_content="""\
package com.google.gson.functional;

import static org.junit.Assert.assertThrows;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.junit.Test;

// https://github.com/google/gson/issues/630: JsonElement.getAsInt() on a value that
// overflows int range (e.g. from exponential notation) silently returns a truncated/
// wrong value instead of throwing.
public class JsonElementGetAsIntOverflow630Test {
  @Test
  public void testGetAsIntThrowsOnOutOfRangeExponentialValue() {
    JsonObject jsonObj = JsonParser.parseString("{\\"id\\":1e50}").getAsJsonObject();
    assertThrows(RuntimeException.class, () -> jsonObj.get("id").getAsInt());
  }
}
""",
        test_cmd=_gson_cmd("JsonElementGetAsIntOverflow630Test"),
    ),
    BugSpec(
        key="gson#600",
        source_repo="google/gson",
        source_issue_number=600,
        base_branch="main",
        new_test_file="gson/src/test/java/com/google/gson/functional/BooleanFromArbitraryString600Test.java",
        new_test_file_content="""\
package com.google.gson.functional;

import static org.junit.Assert.assertThrows;

import com.google.gson.Gson;
import org.junit.Test;

// https://github.com/google/gson/issues/600: deserializing an arbitrary JSON string
// (e.g. "ABC") into a boolean field raises no error and silently sets the field false,
// while a JSON number in the same position correctly raises an error.
public class BooleanFromArbitraryString600Test {
  public static class HasBoolean {
    public boolean isPRA;
  }

  @Test
  public void testBooleanFieldRejectsNonBooleanString() {
    assertThrows(RuntimeException.class, () ->
        new Gson().fromJson("{\\"isPRA\\":\\"ABC\\"}", HasBoolean.class));
  }
}
""",
        test_cmd=_gson_cmd("BooleanFromArbitraryString600Test"),
    ),
    BugSpec(
        key="gson#523",
        source_repo="google/gson",
        source_issue_number=523,
        base_branch="main",
        new_test_file="gson/src/test/java/com/google/gson/functional/JsonPrimitiveNumericHashCode523Test.java",
        new_test_file_content="""\
package com.google.gson.functional;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import com.google.gson.JsonPrimitive;
import org.junit.Test;

// https://github.com/google/gson/issues/523: JsonPrimitive.equals() considers a
// JsonPrimitive(1) (int) equal to JsonPrimitive(1d) (double), but their hashCode()s
// differ -- violating the hashCode/equals contract.
public class JsonPrimitiveNumericHashCode523Test {
  @Test
  public void testEqualNumericPrimitivesHaveSameHashCode() {
    JsonPrimitive p1 = new JsonPrimitive(1);
    JsonPrimitive p2 = new JsonPrimitive(1d);
    assertTrue(p1.equals(p2));
    assertEquals(p1.hashCode(), p2.hashCode());
  }
}
""",
        test_cmd=_gson_cmd("JsonPrimitiveNumericHashCode523Test"),
    ),
    BugSpec(
        key="gson#2638",
        source_repo="google/gson",
        source_issue_number=2638,
        base_branch="main",
        new_test_file="gson/src/test/java/com/google/gson/functional/SubclassOverriddenFieldSerialize2638Test.java",
        new_test_file_content="""\
package com.google.gson.functional;

import static org.junit.Assert.assertEquals;

import com.google.gson.Gson;
import org.junit.Test;

// https://github.com/google/gson/issues/2638: a subclass that shadows (re-declares) a
// superclass field of the same name can't be serialized at all -- Gson's reflective
// adapter walks the whole class hierarchy and throws on the name collision instead of
// preferring the most-derived (shadowing) field, the way plain Java field access would.
public class SubclassOverriddenFieldSerialize2638Test {
  public static class MyClass {
    int a = 22;
  }

  public static class SubClass extends MyClass {
    int a = 25;
    int b = 12;
  }

  @Test
  public void testSerializesShadowedFieldFromMostDerivedClass() {
    Gson gson = new Gson();
    assertEquals("{\\"a\\":25,\\"b\\":12}", gson.toJson(new SubClass()));
  }
}
""",
        test_cmd=_gson_cmd("SubclassOverriddenFieldSerialize2638Test"),
    ),
    BugSpec(
        key="gson#2817",
        source_repo="google/gson",
        source_issue_number=2817,
        base_branch="main",
        new_test_file="gson/src/test/java/com/google/gson/functional/ReaderDoublePrecisionConsistency2817Test.java",
        new_test_file_content="""\
package com.google.gson.functional;

import static org.junit.Assert.assertThrows;

import com.google.gson.JsonObject;
import com.google.gson.internal.bind.JsonTreeReader;
import org.junit.Test;

// https://github.com/google/gson/issues/2817: JsonReader.nextInt() correctly fails when
// the next token is a double (e.g. 42.123), but JsonTreeReader.nextInt() on the exact
// same value silently casts/truncates instead of failing -- the two JsonReader
// implementations should behave consistently.
public class ReaderDoublePrecisionConsistency2817Test {
  @Test
  public void testJsonTreeReaderRejectsIntWhenNextTokenIsDouble() throws Exception {
    JsonObject json = new JsonObject();
    json.addProperty("value", 42.123);
    JsonTreeReader reader = new JsonTreeReader(json);
    reader.beginObject();
    reader.nextName();
    assertThrows(NumberFormatException.class, reader::nextInt);
  }
}
""",
        test_cmd=_gson_cmd("ReaderDoublePrecisionConsistency2817Test"),
    ),
    BugSpec(
        key="gson#1920",
        source_repo="google/gson",
        source_issue_number=1920,
        base_branch="main",
        new_test_file="gson/src/test/java/com/google/gson/functional/EnumMapKeySerializedName1920Test.java",
        new_test_file_content="""\
package com.google.gson.functional;

import static org.junit.Assert.assertEquals;

import com.google.gson.Gson;
import com.google.gson.annotations.SerializedName;
import com.google.gson.reflect.TypeToken;
import java.lang.reflect.Type;
import java.util.HashMap;
import java.util.Map;
import org.junit.Test;

// https://github.com/google/gson/issues/1920: when an enum with a @SerializedName is
// used as a Map key, serialization ignores @SerializedName (uses enum.toString() via
// String.valueOf() instead) and deserialization then can't map the @SerializedName-based
// JSON key back to the enum, producing a null key.
public class EnumMapKeySerializedName1920Test {
  enum RoomIdentifier {
    @SerializedName("MARKER_NAME")
    ROOM_NAME
  }

  @Test
  public void testMapKeySerializationRespectsSerializedNameAndRoundTrips() {
    Gson gson = new Gson();
    Map<RoomIdentifier, String> slots = new HashMap<>();
    slots.put(RoomIdentifier.ROOM_NAME, "ROOM_NAME_TEST");

    String serialized = gson.toJson(slots);
    assertEquals("{\\"MARKER_NAME\\":\\"ROOM_NAME_TEST\\"}", serialized);

    Type type = new TypeToken<Map<RoomIdentifier, String>>() {}.getType();
    Map<RoomIdentifier, String> deserialized = gson.fromJson(serialized, type);
    assertEquals(RoomIdentifier.ROOM_NAME, deserialized.keySet().iterator().next());
  }
}
""",
        test_cmd=_gson_cmd("EnumMapKeySerializedName1920Test"),
    ),
    BugSpec(
        key="gson#1727",
        source_repo="google/gson",
        source_issue_number=1727,
        base_branch="main",
        new_test_file="gson/src/test/java/com/google/gson/functional/LongOverflowFromJson1727Test.java",
        new_test_file_content="""\
package com.google.gson.functional;

import static org.junit.Assert.assertThrows;

import com.google.gson.Gson;
import org.junit.Test;

// https://github.com/google/gson/issues/1727: gson.fromJson(json, Long.class) on a value
// one past Long.MAX_VALUE silently clamps to Long.MAX_VALUE instead of throwing, even
// though JsonPrimitive.getAsLong() and Long.valueOf() both correctly throw
// NumberFormatException for the identical input.
public class LongOverflowFromJson1727Test {
  @Test
  public void testFromJsonRejectsLongOverflow() {
    Gson gson = new Gson();
    assertThrows(RuntimeException.class, () -> gson.fromJson("9223372036854775808", Long.class));
  }
}
""",
        test_cmd=_gson_cmd("LongOverflowFromJson1727Test"),
    ),
    BugSpec(
        key="gson#2769",
        source_repo="google/gson",
        source_issue_number=2769,
        base_branch="main",
        new_test_file="gson/src/test/java/com/google/gson/functional/LenientReaderAfterNull2769Test.java",
        new_test_file_content="""\
package com.google.gson.functional;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

import com.google.gson.internal.bind.TypeAdapters;
import com.google.gson.stream.JsonReader;
import com.google.gson.stream.JsonWriter;
import com.google.gson.stream.Strictness;
import java.io.StringReader;
import java.io.StringWriter;
import org.junit.Test;

// https://github.com/google/gson/issues/2769: with a LENIENT JsonReader, writing a null
// followed by a string value and then reading them back returns the null correctly but
// then reads the following string value as garbage (throws or returns a mangled value)
// instead of the actual string -- lenient mode desyncs its position tracking right after
// a null.
public class LenientReaderAfterNull2769Test {
  @Test
  public void testLenientReaderCorrectlyReadsValueAfterNull() throws Exception {
    StringWriter str = new StringWriter();
    try (JsonWriter writer = new JsonWriter(str)) {
      writer.setStrictness(Strictness.LENIENT);
      TypeAdapters.STRING.write(writer, null);
      TypeAdapters.STRING.write(writer, "value1");
      writer.flush();
    }

    JsonReader reader = new JsonReader(new StringReader(str.toString()));
    reader.setStrictness(Strictness.LENIENT);

    assertNull(TypeAdapters.STRING.read(reader));
    assertEquals("value1", TypeAdapters.STRING.read(reader));
  }
}
""",
        test_cmd=_gson_cmd("LenientReaderAfterNull2769Test"),
    ),
    BugSpec(
        key="gson#453",
        source_repo="google/gson",
        source_issue_number=453,
        base_branch="main",
        new_test_file="gson/src/test/java/com/google/gson/functional/ContextDeserializeExponentNumber453Test.java",
        new_test_file_content="""\
package com.google.gson.functional;

import static org.junit.Assert.assertEquals;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonDeserializationContext;
import com.google.gson.JsonDeserializer;
import com.google.gson.JsonElement;
import java.lang.reflect.Type;
import org.junit.Test;

// https://github.com/google/gson/issues/453: Gson's normal fromJson() entry point parses
// a number in exponential notation (e.g. 1.02e+12) into a long field fine, but the same
// value routed through JsonDeserializationContext.deserialize() from inside a custom
// JsonDeserializer fails to parse it -- the two entry points should be consistent.
public class ContextDeserializeExponentNumber453Test {
  public static class Content {
    long dateCreated;
  }

  public static class Wrapper {
    Content content;
  }

  @Test
  public void testContextDeserializeHandlesExponentNotationLikeDirectFromJson() {
    String innerJson = "{\\"dateCreated\\": 1.020204000000e+12}";

    Content viaDirect = new Gson().fromJson(innerJson, Content.class);
    assertEquals(1020204000000L, viaDirect.dateCreated);

    String wrapperJson = "{\\"content\\":" + innerJson + "}";
    Gson customGson = new GsonBuilder()
        .registerTypeAdapter(Wrapper.class, new JsonDeserializer<Wrapper>() {
          @Override
          public Wrapper deserialize(JsonElement json, Type typeOfT, JsonDeserializationContext context) {
            Wrapper w = new Wrapper();
            w.content = context.deserialize(json.getAsJsonObject().get("content"), Content.class);
            return w;
          }
        })
        .create();
    Wrapper viaContext = customGson.fromJson(wrapperJson, Wrapper.class);
    assertEquals(1020204000000L, viaContext.content.dateCreated);
  }
}
""",
        test_cmd=_gson_cmd("ContextDeserializeExponentNumber453Test"),
    ),
    BugSpec(
        key="gson#1575",
        source_repo="google/gson",
        source_issue_number=1575,
        base_branch="main",
        new_test_file="gson/src/test/java/com/google/gson/functional/JsonStreamParserEmptyString1575Test.java",
        new_test_file_content="""\
package com.google.gson.functional;

import static org.junit.Assert.assertFalse;

import com.google.gson.JsonStreamParser;
import java.io.StringReader;
import org.junit.Test;

// https://github.com/google/gson/issues/1575: JsonStreamParser(emptyString).hasNext()
// throws JsonIOException instead of returning false for genuinely empty input.
public class JsonStreamParserEmptyString1575Test {
  @Test
  public void testHasNextReturnsFalseForEmptyInputInsteadOfThrowing() {
    JsonStreamParser parser = new JsonStreamParser(new StringReader(""));
    assertFalse(parser.hasNext());
  }
}
""",
        test_cmd=_gson_cmd("JsonStreamParserEmptyString1575Test"),
    ),
    BugSpec(
        key="gson#1397",
        source_repo="google/gson",
        source_issue_number=1397,
        base_branch="main",
        new_test_file="gson/src/test/java/com/google/gson/functional/ExposeOverridesTransientExclusion1397Test.java",
        new_test_file_content="""\
package com.google.gson.functional;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.annotations.Expose;
import org.junit.Test;

// https://github.com/google/gson/issues/1397: an explicit @Expose(serialize = true) on a
// transient field should take precedence over Gson's default exclusion of transient
// fields, but the transient modifier still wins and the field is dropped.
public class ExposeOverridesTransientExclusion1397Test {
  public static class HasExposedTransientField {
    @Expose(serialize = true, deserialize = true)
    transient int value = 5;
  }

  @Test
  public void testExposedTransientFieldIsSerialized() {
    Gson gson = new GsonBuilder().excludeFieldsWithoutExposeAnnotation().create();
    String json = gson.toJson(new HasExposedTransientField());
    JsonObject obj = JsonParser.parseString(json).getAsJsonObject();
    assertTrue("expected 'value' to be present in: " + json, obj.has("value"));
    assertEquals(5, obj.get("value").getAsInt());
  }
}
""",
        test_cmd=_gson_cmd("ExposeOverridesTransientExclusion1397Test"),
    ),
    BugSpec(
        key="gson#996",
        source_repo="google/gson",
        source_issue_number=996,
        base_branch="main",
        new_test_file="gson/src/test/java/com/google/gson/functional/NonIntegralGetAsInt996Test.java",
        new_test_file_content="""\
package com.google.gson.functional;

import static org.junit.Assert.assertThrows;

import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import org.junit.Test;

// https://github.com/google/gson/issues/996: JsonElement.getAsInt() on a non-integral
// value like 6.7 silently truncates to 6 instead of throwing, because
// LazilyParsedNumber's int conversion goes through BigDecimal.intValue() (which
// truncates) rather than a form that rejects a non-integral value.
public class NonIntegralGetAsInt996Test {
  @Test
  public void testGetAsIntRejectsNonIntegralValue() {
    JsonElement elem = JsonParser.parseString("6.7");
    assertThrows(RuntimeException.class, elem::getAsInt);
  }
}
""",
        test_cmd=_gson_cmd("NonIntegralGetAsInt996Test"),
    ),
]
