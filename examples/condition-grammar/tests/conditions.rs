use condition_grammar::{Node, NodeRef, ParseResult, Rule, parse};

fn nodes_of(result: &ParseResult<'_>, rule: Rule) -> Vec<NodeRef> {
    fn visit(result: &ParseResult<'_>, node: NodeRef, rule: Rule, out: &mut Vec<NodeRef>) {
        if result.cst.match_rule(node, rule) {
            out.push(node);
        }
        for child in result.cst.children(node) {
            visit(result, child, rule, out);
        }
    }
    let mut nodes = Vec::new();
    visit(result, NodeRef::ROOT, rule, &mut nodes);
    nodes
}

fn texts_of<'a>(result: &ParseResult<'a>, rule: Rule) -> Vec<&'a str> {
    nodes_of(result, rule)
        .into_iter()
        .map(|node| &result.cst.source()[result.cst.span(node)])
        .collect()
}

fn assert_lossless(result: &ParseResult<'_>, source: &str) {
    fn tokens(result: &ParseResult<'_>, node: NodeRef, text: &mut String) {
        match result.cst.get(node) {
            Node::Token(_, index) => text.push_str(result.cst.span_text(index)),
            Node::Rule(..) => {
                for child in result.cst.children(node) {
                    tokens(result, child, text);
                }
            }
        }
    }
    let mut text = String::new();
    tokens(result, NodeRef::ROOT, &mut text);
    assert_eq!(
        text, source,
        "every original token, comment and whitespace must survive"
    );
}

#[test]
fn if_body_braces_are_not_consumed_as_a_struct_literal() {
    // Without the condition mode, ready {} becomes a struct and the body is missing.
    let source = "if ready { Point {}; } Point {};";
    let result = parse(source);
    assert!(
        result.diagnostics.is_empty(),
        "{:?}\n{}",
        result.diagnostics,
        result.cst
    );
    assert_eq!(texts_of(&result, Rule::Condition), ["ready"]);
    assert_eq!(texts_of(&result, Rule::Block), ["{ Point {}; }"]);
    assert_eq!(
        texts_of(&result, Rule::StructExpr),
        ["Point {}", "Point {}"]
    );
    assert_lossless(&result, source);
}

#[test]
fn parentheses_allow_structs_and_restore_the_restricted_condition() {
    // Resetting to true instead of restoring false would make this illegal suffix valid.
    let source = "if (ready) == Point {} {}";
    let result = parse(source);
    assert!(!result.diagnostics.is_empty());
    assert!(
        texts_of(&result, Rule::StructExpr).is_empty(),
        "{}",
        result.cst
    );
    assert_eq!(texts_of(&result, Rule::Condition), ["(ready) == Point"]);
    assert_lossless(&result, source);
}

#[test]
fn parenthesized_struct_conditions_keep_their_own_body() {
    let source = "if value == (Point { x: 1, nested: Point {} }) { Point {}; }";
    let result = parse(source);
    assert!(
        result.diagnostics.is_empty(),
        "{:?}\n{}",
        result.diagnostics,
        result.cst
    );
    assert_eq!(
        texts_of(&result, Rule::Condition),
        ["value == (Point { x: 1, nested: Point {} })"]
    );
    assert_eq!(texts_of(&result, Rule::Block), ["{ Point {}; }"]);
    assert_eq!(
        texts_of(&result, Rule::StructExpr),
        ["Point { x: 1, nested: Point {} }", "Point {}", "Point {}"]
    );
    assert_lossless(&result, source);
}

#[test]
fn nested_conditions_and_parentheses_restore_normal_expressions() {
    let source = "if ((Point {})) { if (ready) { Point {}; } Point { x: 1 }; } Point {};";
    let result = parse(source);
    assert!(
        result.diagnostics.is_empty(),
        "{:?}\n{}",
        result.diagnostics,
        result.cst
    );
    assert_eq!(
        texts_of(&result, Rule::Condition),
        ["((Point {}))", "(ready)"]
    );
    assert_eq!(
        texts_of(&result, Rule::StructExpr),
        ["Point {}", "Point {}", "Point { x: 1 }", "Point {}"]
    );
    // These assertions are outside callbacks, so a skipped essential hook fails.
    assert_eq!(result.trace.condition_entries, 2);
    assert_eq!(result.trace.paren_entries, 3);
    assert_eq!(result.trace.mode_exits, 5);
    assert!(result.trace.struct_predicates >= 4);
    assert_eq!(result.trace.depth, 0);
    assert!(result.trace.struct_literals_allowed);
    assert_lossless(&result, source);
}

#[test]
fn malformed_parentheses_report_errors_and_leave_following_structs_usable() {
    for source in [
        "if (ready == ) {} Point {};",
        "if (1 { Point {}; } Point {};",
        "if (Point { x: }) {} Point {};",
    ] {
        let result = parse(source);
        assert!(
            !result.diagnostics.is_empty(),
            "expected a syntax diagnostic for {source}"
        );
        let statements = texts_of(&result, Rule::ExprStmt);
        assert_eq!(statements.last(), Some(&"Point {};"), "{}", result.cst);
        assert_eq!(
            texts_of(&result, Rule::StructExpr).last(),
            Some(&"Point {}"),
            "{}",
            result.cst
        );
        assert_eq!(result.trace.condition_entries, 1);
        assert_eq!(result.trace.paren_entries, 1);
        assert_eq!(result.trace.mode_exits, 2);
        assert_eq!(result.trace.depth, 0);
        assert!(result.trace.struct_literals_allowed);
        assert_lossless(&result, source);
    }
}

#[test]
fn ordinary_structs_comments_and_repeated_parses_are_lossless() {
    let source = "// café\nPoint { x: 1 + 2, nested: Point {} };\n";
    for _ in 0..3 {
        let result = parse(source);
        assert!(
            result.diagnostics.is_empty(),
            "{:?}\n{}",
            result.diagnostics,
            result.cst
        );
        assert_eq!(
            texts_of(&result, Rule::StructExpr),
            ["Point { x: 1 + 2, nested: Point {} }", "Point {}"]
        );
        assert_eq!(result.trace.condition_entries, 0);
        assert_eq!(result.trace.paren_entries, 0);
        assert_eq!(result.trace.mode_exits, 0);
        assert!(result.trace.struct_predicates >= 2);
        assert_lossless(&result, source);
    }
}
