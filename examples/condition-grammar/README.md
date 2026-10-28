# Struct expressions inside conditions

Keep one expression grammar when `{` can start either a struct literal or an `if` body. This small [lelwel](https://github.com/0x2a-42/lelwel) example uses parser context to restrict only the ambiguous suffix. Parentheses temporarily allow struct literals again.

```text
Point {};                     // ordinary expression: accepted
if ready { Point {}; }        // ready is a name; braces belong to the body
if value == (Point {}) {}      // parenthesized struct: accepted
if value == Point {} {}        // bare struct in the condition: rejected
```

## Run

With a Rust toolchain supporting edition 2024, run from this directory:

```sh
cargo test --locked
cargo run --locked -- examples/valid.txt
cargo run --locked -- examples/invalid.txt
```

The command prints the native concrete syntax tree. Valid input exits `0`; invalid syntax prints diagnostics and exits `1`. A missing/unreadable input file exits `2`. The invalid example is expected to fail.

The dependencies are pinned to lelwel **0.10.4**, Logos **0.16.1** and codespan-reporting **0.13.1**; `Cargo.lock` pins their dependencies. The checks were run with Rust/Cargo **1.98.1** on macOS. Earlier toolchains were not tested.

## The grammar

[conditions.llw](src/conditions.llw) contains just one `expr` rule. Its relevant pieces are:

```antlr
condition: #1 expr #2;

// Inside expr:
| Name @name_expr [?1 '{' [field (',' field)*] '}' @struct_expr]
| '(' #1 expr #2 ')' @paren_expr
```

The action and predicate numbers are local to their rule:

| Callback in [parser.rs](src/parser.rs) | Effect |
| --- | --- |
| `action_condition_1` | Save the previous mode and disallow struct-literal suffixes. |
| `action_condition_2` | Restore the saved mode before parsing the body. |
| `action_expr_1` | Save the previous mode and allow struct literals inside parentheses. |
| `action_expr_2` | Restore the saved mode before expecting the closing parenthesis. |
| `predicate_expr_1` | Allow the optional `{ ... }` suffix only in the current mode. |

Restore the previous value instead of resetting it to `true`. A parenthesized expression inside a condition must return to the restricted mode. A stack also handles nested parentheses. After the condition, the body and later ordinary expressions return to their original mode.

The callbacks implement lelwel's `ParserCallbacks::Context`; `build.rs` invokes the published generator normally. Keep the hand-written lexer and callbacks. The generated parser is written into Cargo's build directory and is not edited.

## Checks and scope

The tests inspect real CST nodes and source spans, reconstruct every original token, and check diagnostics. They cover body/condition boundaries, nested struct fields, nested conditions and parentheses, repeated parses, comments, and recovery from missing or malformed parentheses followed by another usable struct statement. Separate execution counters are checked outside the callbacks so skipped mode actions or an unused predicate cannot silently satisfy the tests. CLI tests check actual output and exit status.

This is a teaching language with names, integers, `+`, `==`, structs, semicolon statements and `if` blocks. It is not a complete Rust or Go grammar. It omits trailing field commas and broader language semantics. The recovery checks cover the included fixtures; they are not a guarantee for every malformed input. These are scripted checks; the original author's grammar and adoption have not been tested.

When extending it, pair each mode entry with a restore action. The example uses neither ordered-choice backtracking nor early-return operators around these actions. Recheck restoration if adding either: ordinary context mutations are not automatically rolled back with a speculative parse.

References: [lelwel grammar specification and callbacks](https://github.com/0x2a-42/lelwel#semantic-actions-predicates-and-assertions), [official C parser context example](https://github.com/0x2a-42/lelwel/blob/main/examples/c/src/parser.rs), [original question](https://github.com/0x2a-42/lelwel/issues/73).

## Optional coffee

This example is free. If it saves you time, a small coffee is welcome and entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
