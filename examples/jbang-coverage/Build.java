///usr/bin/env jbang "$0" "$@" ; exit $?
//JAVA 25+
//SOURCES src/main/java/**/*

void main(String... args) {
    System.out.println(new example.Greeting().message(args.length == 0 ? "" : args[0]));
}
