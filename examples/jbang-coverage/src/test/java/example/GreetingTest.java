package example;

import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

class GreetingTest {
    @Test
    void greetsNamedPerson() throws Exception {
        assertEquals("Hello, Ada", new Greeting().message("Ada"));
        mark("named");
    }

    @Test
    void greetsStranger() throws Exception {
        assertEquals("Hello, stranger", new Greeting().message(""));
        mark("stranger");
    }

    private void mark(String name) throws Exception {
        var directory = Path.of("build", "test-markers");
        Files.createDirectories(directory);
        Files.writeString(directory.resolve(name), "executed\n");
    }
}
