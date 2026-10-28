use codespan_reporting::{
    files::SimpleFile,
    term::{
        self, Config,
        termcolor::{ColorChoice, StandardStream},
    },
};
use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<_> = std::env::args_os().collect();
    if args.len() != 2 {
        eprintln!("Usage: condition-grammar <source-file>");
        return ExitCode::from(2);
    }
    let source = match std::fs::read_to_string(&args[1]) {
        Ok(source) => source,
        Err(error) => {
            eprintln!("Could not read source: {error}");
            return ExitCode::from(2);
        }
    };
    let result = condition_grammar::parse(&source);
    print!("{}", result.cst);
    let writer = StandardStream::stderr(ColorChoice::Auto);
    let file = SimpleFile::new(args[1].to_string_lossy(), &source);
    for diagnostic in &result.diagnostics {
        if let Err(error) =
            term::emit_to_write_style(&mut writer.lock(), &Config::default(), &file, diagnostic)
        {
            eprintln!("Could not display diagnostic: {error}");
            return ExitCode::from(2);
        }
    }
    if result.diagnostics.is_empty() {
        ExitCode::SUCCESS
    } else {
        ExitCode::from(1)
    }
}
