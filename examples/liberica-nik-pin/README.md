# Pin an exact Liberica Native Image Kit release

In setup-graalvm v1.6.10, the Liberica selector reads `java-version` and filters the BellSoft release tags with a SemVer parser. The tag `jdk-25.0.5.0.3+6` has more than three numeric parts before the build metadata, so the selector skips it. BellSoft publishes the exact build as a downloadable archive. [Liberica selection code](https://github.com/graalvm/setup-graalvm/blob/v1.6.10/src/liberica.ts#L18-L41) · [setup-graalvm distribution switch](https://github.com/graalvm/setup-graalvm/blob/v1.6.10/src/main.ts#L63-L85) · [BellSoft release](https://github.com/bell-sw/LibericaNIK/releases/tag/jdk-25.0.5.0.3%2B6)

[install-nik.sh](install-nik.sh) finds the archive for Apple Silicon macOS or glibc Linux ARM64, checks its SHA-256 against the release and extracts it into a new directory. It prints the absolute Java home. The non-FX archives in this example already include `native-image`.

## Use it in GitHub Actions

Copy `install-nik.sh` to the root of your repository. Use an ARM64 runner such as `ubuntu-24.04-arm` or `macos-15`. Put this step after checkout in the job that needs this release. Use it as the Java setup step for that job.

```yaml
- name: Install Liberica Native Image Kit
  shell: bash
  run: |
    home="$(bash ./install-nik.sh "$RUNNER_TEMP/liberica-nik")"
    printf 'JAVA_HOME=%s\nGRAALVM_HOME=%s\n' "$home" "$home" >> "$GITHUB_ENV"
    printf '%s/bin\n' "$home" >> "$GITHUB_PATH"

- name: Check the selected build
  shell: bash
  run: |
    java -version
    native-image --version
```

The version steps should report `25.0.5.0.3` and the runtime build `25.0.5.0.3+6-LTS`. [GitHub-hosted runner labels](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) · [Actions environment files](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#environment-files)

## Try the installed compiler

Run the following from this example directory in Bash. You need a C toolchain and the platform's native development libraries. The installer uses the vendor download by default. To use the same archive from a local file, add its path as the second argument; the checksum check still runs.

```sh
JAVA_HOME="$(bash ./install-nik.sh "$(mktemp -d)/nik")" || exit
export JAVA_HOME
export GRAALVM_HOME="$JAVA_HOME"
export PATH="$JAVA_HOME/bin:$PATH"

java -version
native-image --version
javac Hello.java
native-image --no-fallback Hello hello
./hello
```

The program prints `Hello from Native Image`. A file with the wrong checksum stops the installer before extraction. Use a different platform's archive and checksum from the same BellSoft release if you need to adapt the installer for another architecture. [Native Image build prerequisites](https://www.graalvm.org/latest/reference-manual/native-image/#prerequisites)

The sample program was compiled and run on an Apple Silicon Mac and in an Ubuntu 24.04 ARM64 container. The GitHub Actions snippet uses the same installer.

## Optional coffee

If this example saved you some time, you're welcome to buy me a coffee. It's entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
