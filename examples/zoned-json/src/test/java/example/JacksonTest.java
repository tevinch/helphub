package example;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;
import example.ZonedJson.Example;

import java.time.ZoneId;
import java.time.ZonedDateTime;

import static org.junit.jupiter.api.Assertions.assertEquals;

class JacksonTest {

    private static final JsonMapper JSON_MAPPER =
            ZonedJson.mapper();

    private static final ZonedDateTime ZONED_DATE_TIME = ZonedDateTime.of(
            2026, 10, 29,
            13, 12, 0, 666161,
            ZoneId.of("Europe/Berlin")
    );

    private static final Example EXAMPLE_INSTANCE = new Example(ZONED_DATE_TIME);

    private static final String EXPECTED_JSON_STRING =
            "{\"zonedDateTime\":\"2026-10-29T13:12:00.000666161+01:00[Europe/Berlin]\"}";

    @Test
    void creatingAndParsingJsonWorks() {

        String jsonString = JSON_MAPPER.writeValueAsString(EXAMPLE_INSTANCE);

        Example result = JSON_MAPPER.readValue(jsonString, Example.class);

        assertEquals(EXAMPLE_INSTANCE, result);
    }

    @Test
    void creatingJsonWorks() {
        String jsonString = JSON_MAPPER.writeValueAsString(EXAMPLE_INSTANCE);

        assertEquals(
                EXPECTED_JSON_STRING,
                jsonString
        );
    }

    @Test
    void parsingJsonWorks() {
        Example parsed = JSON_MAPPER.readValue(
                EXPECTED_JSON_STRING,
                Example.class);

        assertEquals(
                EXAMPLE_INSTANCE,
                parsed
        );
    }


}
