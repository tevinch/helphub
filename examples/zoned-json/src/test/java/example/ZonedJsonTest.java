package example;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import tools.jackson.databind.json.JsonMapper;

import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

class ZonedJsonTest {
    private final JsonMapper mapper = ZonedJson.mapper();

    @BeforeAll
    static void reportProcessTimezone() {
        System.out.println("Process timezone: " + ZoneId.systemDefault());
        System.out.println("Jackson version: " + ZonedJson.mapper().version());
    }

    static Stream<Arguments> berlinDates() {
        return Stream.of(
            Arguments.of("2026-10-29T13:12:00.000666161+01:00[Europe/Berlin]",
                "2026-10-29T12:12:00.000666161Z", 3600),
            Arguments.of("2026-06-29T13:12:00.000666161+02:00[Europe/Berlin]",
                "2026-06-29T11:12:00.000666161Z", 7200),
            Arguments.of("2026-12-29T13:12:00.000666161+01:00[Europe/Berlin]",
                "2026-12-29T12:12:00.000666161Z", 3600)
        );
    }

    @ParameterizedTest
    @MethodSource("berlinDates")
    void preservesNamedRegionInstantLocalTimeAndNanoseconds(
            String timestamp, String expectedInstant, int expectedOffsetSeconds) {
        String expectedJson = "{\"zonedDateTime\":\"" + timestamp + "\"}";
        ZonedDateTime input = ZonedDateTime.parse(timestamp);
        ZonedJson.Example original = new ZonedJson.Example(input);

        String json = mapper.writeValueAsString(original);
        assertEquals(expectedJson, json);
        ZonedJson.Example parsed = mapper.readValue(expectedJson, ZonedJson.Example.class);
        ZonedJson.Example roundTripped = mapper.readValue(json, ZonedJson.Example.class);

        for (ZonedJson.Example result : new ZonedJson.Example[]{parsed, roundTripped}) {
            ZonedDateTime actual = result.getZonedDateTime();
            assertEquals(original, result);
            assertEquals(ZoneId.of("Europe/Berlin"), actual.getZone());
            assertEquals(Instant.parse(expectedInstant), actual.toInstant());
            assertEquals(input.toLocalDate(), actual.toLocalDate());
            assertEquals(13, actual.getHour());
            assertEquals(12, actual.getMinute());
            assertEquals(0, actual.getSecond());
            assertEquals(666161, actual.getNano());
            assertEquals(expectedOffsetSeconds, actual.getOffset().getTotalSeconds());
        }
        assertSame(input, original.getZonedDateTime());
    }

    @Test
    void repeatedRoundTripsLeaveTheOriginalValueAndObjectUntouched() {
        String json = "{\"zonedDateTime\":\"2026-10-29T13:12:00.000666161+01:00[Europe/Berlin]\"}";
        ZonedDateTime value = ZonedDateTime.of(2026, 10, 29, 13, 12, 0, 666161,
            ZoneId.of("Europe/Berlin"));
        ZonedJson.Example original = new ZonedJson.Example(value);
        ZonedJson.Example current = original;
        for (int pass = 0; pass < 5; pass++) {
            assertEquals(json, mapper.writeValueAsString(current));
            current = mapper.readValue(mapper.writeValueAsString(current), ZonedJson.Example.class);
            assertEquals(original, current);
            assertEquals(ZoneId.of("Europe/Berlin"), current.getZonedDateTime().getZone());
            assertEquals(Instant.parse("2026-10-29T12:12:00.000666161Z"),
                current.getZonedDateTime().toInstant());
            assertEquals(666161, current.getZonedDateTime().getNano());
            assertSame(value, original.getZonedDateTime());
        }
    }
}
