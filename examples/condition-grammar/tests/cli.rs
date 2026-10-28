use std::{path::Path, process::Command};

#[test]
fn valid_file_prints_the_native_tree() {
    let fixture = Path::new(env!("CARGO_MANIFEST_DIR")).join("examples/valid.txt");
    let output = Command::new(env!("CARGO_BIN_EXE_condition-grammar"))
        .arg(fixture)
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let tree = String::from_utf8(output.stdout).unwrap();
    assert!(tree.contains("condition ["));
    assert!(tree.contains("struct_expr ["));
    assert!(tree.contains("block ["));
    assert!(output.stderr.is_empty());
}

#[test]
fn invalid_condition_emits_a_diagnostic_and_exit_one() {
    let fixture = Path::new(env!("CARGO_MANIFEST_DIR")).join("examples/invalid.txt");
    let output = Command::new(env!("CARGO_BIN_EXE_condition-grammar"))
        .arg(fixture)
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&output.stderr).contains("error:"));
    assert!(String::from_utf8_lossy(&output.stdout).contains("condition ["));
}

#[test]
fn missing_input_explains_usage_and_exits_two() {
    let output = Command::new(env!("CARGO_BIN_EXE_condition-grammar"))
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr).contains("Usage:"));
}
