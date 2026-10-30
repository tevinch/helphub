# JUnit coverage with JBang

Run JUnit tests and produce JaCoCo HTML and XML reports for a JBang source project. The example keeps separate application and test entry points and needs no Maven or Gradle build.

Starting JaCoCo's `LoggerRuntime` alone does not instrument application classes. Use JBang's documented `--javaagent` option to attach JaCoCo when the test JVM starts, then use JaCoCo's CLI to generate the reports.

## Run the example

Use JBang 0.142.0 and JDK 25. The commands below were checked with Temurin 25.0.5, JUnit Jupiter 5.11.0, JUnit Platform 1.11.0 and JaCoCo 0.8.16. Dependency downloads require internet access on the first run.

From this directory, run the application:

```sh
jbang Build.java Ada
```

It prints `Hello, Ada`. `Build.java` includes `src/main/java`; `Test.java` includes `Build.java` and `src/test/java`. The JUnit launcher runs the tests in the `example` package.

The following paths contain generated output for this example. Remove those previous outputs before each coverage run so old class dumps and reports cannot enter the new report:

```sh
rm -rf build/classes build/coverage build/test-markers
rm -f build/jacoco.exec build/coverage.xml
mkdir -p build/classes

jbang --javaagent='org.jacoco:org.jacoco.agent:0.8.16:runtime=destfile=build/jacoco.exec,append=false,sessionid=junit,includes=example.Greeting:example.Untested' \
  Test.java

jar --extract --file "$(jbang info jar Test.java)" --dir build/classes \
  example/Greeting.class example/Untested.class

jbang org.jacoco:org.jacoco.cli:0.8.16:nodeps report \
  build/jacoco.exec \
  --classfiles build/classes \
  --sourcefiles src/main/java \
  --html build/coverage \
  --xml build/coverage.xml
```

Open `build/coverage/index.html`. The XML report is `build/coverage.xml`.

Expect two successful JUnit tests. Both branches of `Greeting.message` are covered; `Greeting.unused` remains uncovered. The separate `Untested` class has no coverage, even though the tests never load it. The full report has four covered lines and three missed lines. Each successful test also writes its own file under `build/test-markers`, making it easy to see that both test methods executed.

`Test.java` exits with status 1 if tests fail or discovery finds no tests. JaCoCo writes its execution data when the JVM exits, so the report command can also run after a failing test run. A coverage report does not mean that tests passed; keep the test exit status when using these commands in CI.

## Why extract the compiled class files?

JaCoCo needs the same original class bytes for instrumentation and analysis. JBang caches its compiled output; guessing a cache path or recompiling with different settings can give a class-ID mismatch.

`jbang info jar Test.java` finds the compiled JAR for the test entry point. The JDK's `jar` command extracts its production classes for analysis. These are the bytes used by the test JVM; a separate compilation is unnecessary. The explicit extraction list leaves JUnit tests and the launcher out of the application report.

Include every production class in that list, including nested class files where applicable. This also counts classes that the tests never load. `includes` limits instrumentation to the application's classes, `append=false` replaces old execution data, and `sessionid=junit` gives the report a fixed session name.

## Apply it to another source project

Keep your application dependencies, resources and `//SOURCES` directives in `Build.java`, and your test dependencies and resources in `Test.java`. Remove the in-process JaCoCo runtime/analysis code, its imports and the JaCoCo core dependency; the external Java agent and CLI handle coverage. Set the launcher's package selector to your test package.

Change JaCoCo's `includes` value to your application classes, for example `com.example.Main:com.example.TodoList:com.example.TodoItem`. The colon separates class patterns. Update the `jar` extraction list to their compiled paths, such as `com/example/Main.class`, and include all production class files that should count in the report. Quote a nested class entry such as `'com/example/Main$Helper.class'` to keep the shell from interpreting `$`.

Set `--sourcefiles` to the root containing their package directories. Keep generated coverage paths separate from existing project files when adapting the cleanup commands. If sources or compiler settings change, repeat the test run and extraction together before reporting.

The [JBang Java agent documentation](https://www.jbang.dev/documentation/jbang/latest/running.html#java-agents) describes the native launch option. JaCoCo also maintains a [JBang catalog](https://github.com/jacoco/jbang-catalog); the commands here use explicit versions rather than its floating `RELEASE` aliases. See the [JaCoCo runtime options](https://www.jacoco.org/jacoco/trunk/doc/agent.html) and [CLI report options](https://www.jacoco.org/jacoco/trunk/doc/cli.html) for other configurations.

## Validation

Two clean runs executed both JUnit tests and produced matching HTML and XML results, including zero coverage for the never-loaded `Untested` class. JaCoCo's `execinfo` and `classinfo` commands reported the same `Greeting` class ID. Checks also confirmed that removing instrumentation leaves no coverage data, omitting test execution leaves no test markers, zero discovered tests fails, and a failing JUnit assertion returns status 1 while coverage remains reportable. This fixture uses ordinary application code; it does not exercise database integration or a separate test JVM.

## Optional coffee

If this saved you some time, a coffee is welcome, but entirely optional. The example is free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
