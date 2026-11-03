use notify::{Config, Event, EventKind, PollWatcher, RecursiveMode, Watcher};
use std::{
    env,
    error::Error,
    fs,
    path::{Component, Path, PathBuf},
    process::Command,
    sync::mpsc,
    time::Duration,
};

fn relevant(event: &Event, root: &Path) -> bool {
    if matches!(event.kind, EventKind::Access(_)) {
        return false;
    }
    event.paths.is_empty()
        || event.paths.iter().any(|path| {
            path.strip_prefix(root).is_ok_and(|relative| {
                !relative.components().any(|part| {
                matches!(part, Component::Normal(name) if name == ".git" || name == "vendor")
            })
            })
        })
}

fn check_event(event: notify::Result<Event>, root: &Path) -> bool {
    match event {
        Ok(event) => relevant(&event, root),
        Err(error) => {
            eprintln!("[watch error] {error}");
            false
        }
    }
}

fn compile(root: &Path, input: &Path, output: &Path) -> Result<(), Box<dyn Error>> {
    eprintln!("[compile start]");
    let status = Command::new(env::var_os("TYPST").unwrap_or_else(|| "typst".into()))
        .current_dir(root)
        .arg("compile")
        .arg("--root")
        .arg(root)
        .arg(input)
        .arg(output)
        .status()?;
    if status.success() {
        eprintln!("[compile ok]");
    } else {
        eprintln!("[compile failed] {status}; waiting for another source change");
    }
    Ok(())
}

fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<_> = env::args_os().skip(1).collect();
    if args.len() != 3 {
        return Err("Usage: polling-compile SOURCE_ROOT INPUT_RELATIVE_TO_ROOT OUTPUT_PDF\nCreate the output parent directory first; it must be outside SOURCE_ROOT.".into());
    }
    let root = fs::canonicalize(&args[0])?;
    if !root.is_dir() {
        return Err("SOURCE_ROOT must be a directory".into());
    }
    let input = fs::canonicalize(root.join(&args[1]))?;
    if !input.is_file() || !input.starts_with(&root) {
        return Err("Input must be a file inside SOURCE_ROOT".into());
    }
    let requested_output = PathBuf::from(&args[2]);
    if fs::symlink_metadata(&requested_output).is_ok_and(|m| m.file_type().is_symlink()) {
        return Err("Output must not be a symbolic link".into());
    }
    let name = requested_output
        .file_name()
        .ok_or("Output must name a PDF file")?;
    let parent = requested_output
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    let output = fs::canonicalize(parent)?.join(name);
    if output.starts_with(&root) {
        return Err(
            "Output must be outside SOURCE_ROOT, for example in a sibling directory".into(),
        );
    }
    if output
        .extension()
        .is_none_or(|extension| !extension.eq_ignore_ascii_case("pdf"))
    {
        return Err("Output must have a .pdf extension".into());
    }

    let (sender, receiver) = mpsc::channel();
    let config = Config::default()
        .with_poll_interval(Duration::from_millis(200))
        .with_compare_contents(true)
        .with_follow_symlinks(false);
    let mut watcher = PollWatcher::new(
        move |event| {
            let _ = sender.send(event);
        },
        config,
    )?;
    watcher.watch(&root, RecursiveMode::Recursive)?;
    eprintln!(
        "[watch ready] {:?} compare_contents={} interval=200ms; Ctrl+C to stop",
        <PollWatcher as Watcher>::kind(),
        config.compare_contents()
    );

    // Register before compiling so edits made during the initial compile are queued.
    compile(&root, &input, &output)?;
    loop {
        if !check_event(receiver.recv()?, &root) {
            continue;
        }
        // Coalesce a save's burst. Events received during a compile stay in the
        // channel and cause a follow-up; no compiler process is cancelled.
        while let Ok(event) = receiver.recv_timeout(Duration::from_millis(100)) {
            check_event(event, &root);
        }
        compile(&root, &input, &output)?;
    }
}
