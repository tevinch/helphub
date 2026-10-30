package example;

public class Greeting {
    public String message(String name) {
        if (name.isBlank()) {
            return "Hello, stranger";
        }
        return "Hello, " + name;
    }

    public String unused() {
        return "Not called by these tests";
    }
}
