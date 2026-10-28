use crate::parser::{Diagnostic, Span};
use codespan_reporting::diagnostic::Label;
use logos::Logos;

#[derive(Logos, Debug, Copy, Clone, PartialEq, Eq)]
pub enum Token {
    #[token("if")]
    If,
    #[regex(r"[a-zA-Z_][a-zA-Z0-9_]*")]
    Name,
    #[regex(r"[0-9]+")]
    Int,
    #[token("{")]
    LBrace,
    #[token("}")]
    RBrace,
    #[token("(")]
    LPar,
    #[token(")")]
    RPar,
    #[token(";")]
    Semi,
    #[token(":")]
    Colon,
    #[token(",")]
    Comma,
    #[token("==")]
    EqEq,
    #[token("+")]
    Plus,
    #[regex(r"[ \t\r\n]+")]
    Whitespace,
    #[regex(r"//[^\r\n]*", allow_greedy = true)]
    Comment,
    Error,
    EOF,
}

pub fn tokenize(source: &str, diags: &mut Vec<Diagnostic>) -> (Vec<Token>, Vec<Span>) {
    let mut tokens = Vec::new();
    let mut spans = Vec::new();
    for (token, span) in Token::lexer(source).spanned() {
        tokens.push(token.unwrap_or_else(|_| {
            diags.push(
                Diagnostic::error()
                    .with_message("unrecognized character")
                    .with_label(Label::primary((), span.clone())),
            );
            Token::Error
        }));
        spans.push(span);
    }
    (tokens, spans)
}
