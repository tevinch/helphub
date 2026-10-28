use crate::lexer::{Token, tokenize};
use codespan_reporting::diagnostic::Label;
use std::{cell::Cell, rc::Rc};

pub type Diagnostic = codespan_reporting::diagnostic::Diagnostic<()>;
include!(concat!(env!("OUT_DIR"), "/generated.rs"));

/// Execution counters let the example check that the native callbacks actually ran.
#[derive(Debug, Clone, Copy, Default)]
pub struct Trace {
    pub condition_entries: usize,
    pub paren_entries: usize,
    pub mode_exits: usize,
    pub struct_predicates: usize,
    pub depth: usize,
    pub struct_literals_allowed: bool,
}

pub struct Context {
    allow_struct_literals: bool,
    previous_modes: Vec<bool>,
    trace: Rc<Cell<Trace>>,
}

impl Default for Context {
    fn default() -> Self {
        Self {
            allow_struct_literals: true,
            previous_modes: Vec::new(),
            trace: Rc::new(Cell::new(Trace {
                struct_literals_allowed: true,
                ..Trace::default()
            })),
        }
    }
}

impl Context {
    fn enter(&mut self, allow: bool) {
        self.previous_modes.push(self.allow_struct_literals);
        self.allow_struct_literals = allow;
        let mut trace = self.trace.get();
        if allow {
            trace.paren_entries += 1;
        } else {
            trace.condition_entries += 1;
        }
        trace.depth = self.previous_modes.len();
        trace.struct_literals_allowed = allow;
        self.trace.set(trace);
    }

    fn leave(&mut self) {
        self.allow_struct_literals = self
            .previous_modes
            .pop()
            .expect("balanced grammar mode actions");
        let mut trace = self.trace.get();
        trace.mode_exits += 1;
        trace.depth = self.previous_modes.len();
        trace.struct_literals_allowed = self.allow_struct_literals;
        self.trace.set(trace);
    }
}

impl<'a> ParserCallbacks<'a> for Parser<'a> {
    type Diagnostic = Diagnostic;
    type Context = Context;

    fn create_tokens(
        _: &mut Context,
        source: &str,
        diags: &mut Vec<Diagnostic>,
    ) -> (Vec<Token>, Vec<Span>) {
        tokenize(source, diags)
    }

    fn create_diagnostic(&self, span: Span, message: String) -> Diagnostic {
        Diagnostic::error()
            .with_message(message)
            .with_label(Label::primary((), span))
    }

    fn action_condition_1(&mut self, _: &mut Vec<Diagnostic>) {
        self.context.enter(false);
    }
    fn action_condition_2(&mut self, _: &mut Vec<Diagnostic>) {
        self.context.leave();
    }
    fn action_expr_1(&mut self, _: &mut Vec<Diagnostic>) {
        self.context.enter(true);
    }
    fn action_expr_2(&mut self, _: &mut Vec<Diagnostic>) {
        self.context.leave();
    }

    fn predicate_expr_1(&self) -> bool {
        let mut trace = self.context.trace.get();
        trace.struct_predicates += 1;
        self.context.trace.set(trace);
        self.context.allow_struct_literals
    }
}

pub struct ParseResult<'a> {
    pub cst: Cst<'a>,
    pub diagnostics: Vec<Diagnostic>,
    pub trace: Trace,
}

pub fn parse(source: &str) -> ParseResult<'_> {
    let mut diagnostics = Vec::new();
    let context = Context::default();
    let trace = Rc::clone(&context.trace);
    let cst = Parser::new_with_context(source, &mut diagnostics, context).parse(&mut diagnostics);
    ParseResult {
        cst,
        diagnostics,
        trace: trace.get(),
    }
}
