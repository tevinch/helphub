# Preserve a named time zone in Jackson 3 JSON

Keep `Europe/Berlin`, the instant and nanoseconds when writing and reading a `ZonedDateTime`.

Jackson 3 writes an offset without the region ID by default, and adjusts parsed values to the mapper's context time zone. For the round trip in [Jackson issue 6348](https://github.com/FasterXML/jackson-databind/issues/6348), configure both directions:

```java
import tools.jackson.databind.cfg.DateTimeFeature;
import tools.jackson.databind.json.JsonMapper;

JsonMapper mapper = JsonMapper.builder()
    .enable(DateTimeFeature.WRITE_DATES_WITH_ZONE_ID)
    .disable(DateTimeFeature.ADJUST_DATES_TO_CONTEXT_TIME_ZONE)
    .build();
```

`WRITE_DATES_WITH_ZONE_ID` includes `[Europe/Berlin]` in the text. Disabling `ADJUST_DATES_TO_CONTEXT_TIME_ZONE` keeps that parsed region instead of replacing it with the context zone. Keeping just the same instant or `+01:00` offset would not preserve the named region.

These are Jackson 3 `DateTimeFeature` settings. Java time support is included in Jackson 3; no additional JavaTimeModule is needed. The bracketed region follows Java's `ISO_ZONED_DATE_TIME` format; it is an opt-in format for consumers that accept region IDs, rather than an offset-only ISO-8601 representation. See the [versioned feature documentation](https://javadoc.io/static/tools.jackson.core/jackson-databind/3.2.4/tools.jackson.databind/tools/jackson/databind/cfg/DateTimeFeature.html).

## Run

Requires Java 17 or later and Maven 3.9 or later. The POM pins Jackson 3.2.4.

```sh
mvn -q test exec:java
```

The example writes JSON, reads it back into the same POJO and checks that the values are equal:

```text
{"zonedDateTime":"2026-10-29T13:12:00.000666161+01:00[Europe/Berlin]"}
Zone: Europe/Berlin
Instant: 2026-10-29T12:12:00.000666161Z
Nanoseconds: 666161
```

The seven tests include the original three operations, summer/winter offsets and repeated round trips. They check the named region, instant, local time, nanoseconds and preservation of the original object.

To use the other version from the reported example:

```sh
mvn -q clean test exec:java -Djackson.version=3.1.8
```

The example uses public configuration APIs and leaves the POJO unchanged. It does not change Jackson's defaults globally or require a library patch.

## Optional coffee

This example is free. If it saved you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
