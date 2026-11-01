use std::{env, fs, path::PathBuf};

fn main() {
    // This ordinary host executable deliberately uses std. Target startup flags
    // must not be applied when Cargo compiles it.
    let host = env::var("HOST").expect("Cargo supplies HOST");
    let target = env::var("TARGET").expect("Cargo supplies TARGET");
    let output = PathBuf::from(env::var_os("OUT_DIR").expect("Cargo supplies OUT_DIR"));
    fs::write(
        output.join("host-script.json"),
        format!(r#"{{"host":"{host}","target":"{target}"}}"#),
    )
    .expect("write build-script witness");
    println!("cargo:rerun-if-changed=build.rs");
}
