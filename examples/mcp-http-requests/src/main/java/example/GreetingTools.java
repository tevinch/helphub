package example;

import io.quarkiverse.mcp.server.Tool;

public class GreetingTools {
    @Tool(description = "Greet a user by name")
    public String greet(String name) {
        return "Hello, " + name + "!";
    }
}
