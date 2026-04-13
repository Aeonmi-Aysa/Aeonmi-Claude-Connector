"""Tests for the QUBE lexer and parser."""

import pytest

from aeonmi_claude_connector.qube_parser import (
    Binding,
    Bottom,
    Call,
    Collapse,
    ConstructorCall,
    EntropyCredit,
    Entanglement,
    Evolution,
    FlowPipe,
    GlyphLock,
    Identifier,
    Infinity,
    Number,
    ParseError,
    Program,
    QuantumState,
    StringLiteral,
    Superposition,
    parse,
    tokenize,
)
from aeonmi_claude_connector.qube_syntax import TokenType


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

class TestTokenize:
    def test_simple_binding_tokens(self):
        tokens = tokenize("λ x ≔ ∞")
        types = [t.type for t in tokens if t.type != TokenType.NEWLINE]
        assert types == [
            TokenType.LAMBDA,
            TokenType.IDENT,
            TokenType.ASSIGN,
            TokenType.INFINITY,
            TokenType.EOF,
        ]

    def test_number_token(self):
        tokens = [t for t in tokenize("42") if t.type != TokenType.NEWLINE]
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == 42.0

    def test_float_token(self):
        tokens = [t for t in tokenize("3.14") if t.type != TokenType.NEWLINE]
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == pytest.approx(3.14)

    def test_string_token(self):
        tokens = [t for t in tokenize('"hello"') if t.type != TokenType.NEWLINE]
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "hello"

    def test_quantum_state_tokens(self):
        tokens = [t for t in tokenize("|ψ⟩") if t.type != TokenType.NEWLINE]
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        assert TokenType.STATE_OPEN in types
        assert TokenType.PSI in types
        assert TokenType.STATE_CLOSE in types

    def test_comment_skipped(self):
        tokens = [t for t in tokenize("# this is a comment\nλ x ≔ ∞") if t.type != TokenType.NEWLINE]
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        assert types == [TokenType.LAMBDA, TokenType.IDENT, TokenType.ASSIGN, TokenType.INFINITY]

    def test_unknown_char_raises(self):
        with pytest.raises(SyntaxError):
            tokenize("@bad")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class TestParseBinding:
    def test_simple_binding(self):
        ast = parse("λ x ≔ ∞")
        assert isinstance(ast, Program)
        assert len(ast.statements) == 1
        binding = ast.statements[0]
        assert isinstance(binding, Binding)
        assert binding.name == "x"
        assert isinstance(binding.value, Infinity)

    def test_binding_to_number(self):
        ast = parse("λ n ≔ 7")
        binding = ast.statements[0]
        assert isinstance(binding.value, Number)
        assert binding.value.value == 7.0

    def test_binding_to_string(self):
        ast = parse('λ s ≔ "hello"')
        binding = ast.statements[0]
        assert isinstance(binding.value, StringLiteral)
        assert binding.value.value == "hello"

    def test_binding_to_identifier(self):
        ast = parse("λ y ≔ x")
        binding = ast.statements[0]
        assert isinstance(binding.value, Identifier)
        assert binding.value.name == "x"


class TestParseQuantumState:
    def test_psi_state(self):
        ast = parse("|ψ⟩")
        node = ast.statements[0]
        assert isinstance(node, QuantumState)

    def test_string_state(self):
        ast = parse('|"hello"⟩')
        node = ast.statements[0]
        assert isinstance(node, QuantumState)
        assert isinstance(node.content, StringLiteral)


class TestParseOperators:
    def test_entanglement(self):
        ast = parse("|ψ⟩ ⊗ ∞")
        node = ast.statements[0]
        assert isinstance(node, Entanglement)
        assert isinstance(node.left, QuantumState)
        assert isinstance(node.right, Infinity)

    def test_superposition(self):
        ast = parse('|"a"⟩ ⊕ |"b"⟩')
        node = ast.statements[0]
        assert isinstance(node, Superposition)

    def test_flow_pipe(self):
        ast = parse("|ψ⟩ ↝ ∞")
        node = ast.statements[0]
        assert isinstance(node, FlowPipe)

    def test_collapse(self):
        ast = parse("↯ |ψ⟩")
        node = ast.statements[0]
        assert isinstance(node, Collapse)

    def test_evolution(self):
        ast = parse("⟳ |ψ⟩")
        node = ast.statements[0]
        assert isinstance(node, Evolution)

    def test_glyph_lock(self):
        ast = parse("◈ |ψ⟩")
        node = ast.statements[0]
        assert isinstance(node, GlyphLock)

    def test_entropy_credit(self):
        ast = parse("⧖ 50")
        node = ast.statements[0]
        assert isinstance(node, EntropyCredit)
        assert isinstance(node.amount, Number)

    def test_constructor_call(self):
        ast = parse("Æ(∞)")
        node = ast.statements[0]
        assert isinstance(node, ConstructorCall)
        assert len(node.args) == 1
        assert isinstance(node.args[0], Infinity)

    def test_bottom(self):
        ast = parse("⊥")
        node = ast.statements[0]
        assert isinstance(node, Bottom)


class TestParsePrecedence:
    def test_pipe_lower_than_tensor(self):
        # a ↝ b ⊗ c  should be  a ↝ (b ⊗ c)
        ast = parse("|ψ⟩ ↝ ∞ ⊗ ∞")
        node = ast.statements[0]
        assert isinstance(node, FlowPipe)
        assert isinstance(node.target, Entanglement)

    def test_tensor_lower_than_superpose(self):
        # a ⊗ b ⊕ c should be  (a ⊗ (b ⊕ c)) — superpose binds tighter
        # Actually: tensor_expr groups super_expr, so  a ⊗ (b ⊕ c)
        ast = parse("|ψ⟩ ⊗ ∞ ⊕ ∞")
        node = ast.statements[0]
        assert isinstance(node, Entanglement)
        assert isinstance(node.right, Superposition)


class TestParseMultiStatement:
    def test_two_bindings(self):
        src = "λ a ≔ ∞\nλ b ≔ |ψ⟩"
        ast = parse(src)
        assert len(ast.statements) == 2
        assert all(isinstance(s, Binding) for s in ast.statements)

    def test_binding_then_expression(self):
        src = "λ x ≔ ∞\n↯ x"
        ast = parse(src)
        assert len(ast.statements) == 2
        assert isinstance(ast.statements[0], Binding)
        assert isinstance(ast.statements[1], Collapse)


class TestParseErrors:
    def test_missing_assign(self):
        with pytest.raises(ParseError):
            parse("λ x |ψ⟩")

    def test_unclosed_state(self):
        with pytest.raises(ParseError):
            parse("|ψ")

    def test_unexpected_token(self):
        with pytest.raises(ParseError):
            parse("≔ ∞")


class TestParseCall:
    def test_named_call(self):
        ast = parse("sqrt(9)")
        node = ast.statements[0]
        assert isinstance(node, Call)
        assert node.name == "sqrt"
        assert len(node.args) == 1

    def test_multi_arg_call(self):
        ast = parse("foo(1, 2, 3)")
        node = ast.statements[0]
        assert isinstance(node, Call)
        assert len(node.args) == 3
