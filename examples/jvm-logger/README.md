# Call SLF4J from a standalone Rust JVM program

There are two separate requirements: convert Rust's `&str` to a real Java `String`, and put SLF4J's classes on the Java launcher's runtime classpath.

This example targets `rustc_codegen_jvm` commit **`67e89c1b1e6ace5837da7d0a818ecde0c0660638`**, its pinned **nightly-2026-10-23**, and **SLF4J 2.0.20**. It uses the existing compiler and runtime without a Java adapter or a compiler patch. The backend has no tagged release at this revision; use the pinned source rather than assuming an older installed backend has the same interop support.

## Convert the string

The backend represents `&str` as `org.rustlang.runtime.Utf8View`. Declaring `String::new(value: &str)` asks Java for `String(Utf8View)`, which does not exist. Bind the runtime's existing static conversion instead:

```rust
#[jvm::class("java.lang.String")]
impl JavaString {}

#[jvm::class("org.rustlang.runtime.Utf8View")]
impl RustText {
    #[jvm::static_method(name = "toJavaString")]
    pub fn to_java(value: &str) -> *mut JavaString {}
}
```

`RustText::to_java("local.example")` returns a Java `String` reference suitable for `LoggerFactory.getLogger(String)`. Keep `Logger` declared with `#[jvm::interface("org.slf4j.Logger")]`; its `info` method needs interface dispatch. The complete [Rust program](src/main.rs) converts an owned Rust string containing `β` and `🌍`, checks Java's UTF-16 length, gets the real logger, and logs two messages.

The macro's `*mut JavaString` and `*mut Logger` values carry JVM object references. At this pinned revision, calling Rust's `.is_null()` on these handles fails with a `ClassCastException` in the runtime pointer helper. Use the bound Java methods as shown in the program. The Java length assertion and actual logger calls remain required checks of conversion and invocation.

## Build and launch with external jars

Build the pinned backend using its [source setup instructions](https://github.com/IntegralPilot/rustc_codegen_jvm/blob/67e89c1b1e6ace5837da7d0a818ecde0c0660638/cargo-jvm/README.md#from-a-source-checkout). Check out the revision above before installing/setup. Its `rust-toolchain.toml` selects the required dated nightly and components.

From this example directory, with that backend configured:

```sh
cargo jvm package --bin jvm_logger_demo --output app.jar --locked
mkdir -p libs
curl --fail --location --output libs/slf4j-api-2.0.20.jar https://repo.maven.apache.org/maven2/org/slf4j/slf4j-api/2.0.20/slf4j-api-2.0.20.jar
curl --fail --location --output libs/slf4j-simple-2.0.20.jar https://repo.maven.apache.org/maven2/org/slf4j/slf4j-simple/2.0.20/slf4j-simple-2.0.20.jar
java -Xss16m -cp 'app.jar:libs/*' jvm_logger_demo.jvm_logger_demo
```

On Windows, use **`;`** between the classpath entries: `"app.jar;libs/*"`.

`package` includes the Rust runtime in `app.jar`; the two SLF4J jars remain external. `slf4j-api` supplies `Logger` and `LoggerFactory`. `slf4j-simple` is one logging provider; use the provider appropriate for your application instead of loading several providers together.

The pinned `cargo jvm run` launcher uses `java -jar`. Adding `-cp` through `--java-arg` does not solve this: the [Java launcher ignores other classpath settings with `-jar`](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html). Launch the generated main class with `java -cp` as above. You can inspect the JAR's `META-INF/MANIFEST.MF` for its `Main-Class` if you change the crate name.

With both jars, the logger emits `Hello β 🌍` and `second message` under `local.example`, and the Rust program prints `JAVA_STRING_LENGTH=10` and `LOGGING_DONE`. The provider writes log lines to stderr by default. The [SLF4J manual](https://www.slf4j.org/manual.html) explains the API/provider distinction: without a provider, calls can complete with a warning and no log output.

## Reproduce the native checks

With the pinned backend already built and its JDK/Rust tools available:

```sh
python3 check.py /path/to/rustc_codegen_jvm --output check-results
```

The script downloads the two official Maven jars and verifies their pinned SHA-256 checksums before using them. It compiles and runs the original wrong constructor, the corrected Rust program twice, and the incorrect class/interface declaration. It separately checks missing API, missing provider, and `-jar` classpath omission. The missing-provider case deliberately returns successfully but fails the required visible logging result; it is not treated as working logging.

These checks use native Rust compilation, actual Java strings, and the real external SLF4J API/provider. They do not test the original application, a Minecraft/mod-loader deployment, or human manual usage. The wrong-constructor and wrong-dispatch Cargo features exist only to reproduce those failures.

The [native check passed](https://github.com/tevinch/helphub/actions/runs/40914191760) on Ubuntu 24.04.5 with Temurin 25.0.5+8 and the pinned nightly/backend. Both corrected launches produced the expected Java string length, both SLF4J messages and the completion marker. The original constructor, missing API, missing provider, `-jar` classpath omission and incorrect interface dispatch each produced their expected distinct failure or missing-output result. These are software-operated native checks; adoption in the original application remains unverified.

## Optional coffee

This example is free. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
