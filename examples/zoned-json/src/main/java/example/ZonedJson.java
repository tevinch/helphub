package example;

import tools.jackson.databind.cfg.DateTimeFeature;
import tools.jackson.databind.json.JsonMapper;

import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.Objects;

public final class ZonedJson {
    private ZonedJson() {}

    public static JsonMapper mapper() {
        return JsonMapper.builder()
            .enable(DateTimeFeature.WRITE_DATES_WITH_ZONE_ID)
            .disable(DateTimeFeature.ADJUST_DATES_TO_CONTEXT_TIME_ZONE)
            .build();
    }

    public static void main(String[] args) {
        JsonMapper mapper = mapper();
        Example original = new Example(ZonedDateTime.of(
            2026, 10, 29, 13, 12, 0, 666161, ZoneId.of("Europe/Berlin")));
        String json = mapper.writeValueAsString(original);
        Example restored = mapper.readValue(json, Example.class);
        if (!original.equals(restored)) {
            throw new IllegalStateException("The round trip changed the value");
        }
        System.out.println(json);
        System.out.println("Zone: " + restored.getZonedDateTime().getZone());
        System.out.println("Instant: " + restored.getZonedDateTime().toInstant());
        System.out.println("Nanoseconds: " + restored.getZonedDateTime().getNano());
    }

    public static final class Example {
        private ZonedDateTime zonedDateTime;

        public Example() {
            this(null);
        }

        public Example(ZonedDateTime zonedDateTime) {
            this.zonedDateTime = zonedDateTime;
        }

        public ZonedDateTime getZonedDateTime() {
            return zonedDateTime;
        }

        public void setZonedDateTime(ZonedDateTime zonedDateTime) {
            this.zonedDateTime = zonedDateTime;
        }

        @Override
        public boolean equals(Object o) {
            if (o == null || getClass() != o.getClass()) return false;
            Example example = (Example) o;
            return Objects.equals(zonedDateTime, example.zonedDateTime);
        }

        @Override
        public int hashCode() {
            return Objects.hashCode(zonedDateTime);
        }

        @Override
        public String toString() {
            return "Example{" +
                    "zonedDateTime=" + zonedDateTime +
                    '}';
        }
    }
}
