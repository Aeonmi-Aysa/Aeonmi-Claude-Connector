"""QUBE lexer and recursive-descent parser.

Implements the grammar from Aeonmi-Aysa/aeonmi docs/grammar_qube.md and
src/qube/{lexer,parser,ast}.rs.

File format: .qube
Statements: state_decl, gate_apply, collapse, assert_stmt, log_stmt, let_binding, comment
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .qube_syntax import (
    KEYWORDS, QUBIT_STARTERS, SINGLE_CHAR_TOKENS, TWO_QUBIT_GATES, TokenType,
)


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------

@dataclass
class Token:
    type: str
    value: Any
    line: int = 1
    col: int = 1

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r})"


# ---------------------------------------------------------------------------
# AST nodes  (mirrors src/qube/ast.rs)
# ---------------------------------------------------------------------------

@dataclass
class Node:
    pass


@dataclass
class QubeProgram(Node):
    stmts: list[Node] = field(default_factory=list)


@dataclass
class StateDecl(Node):
    """state <name> = <expr>"""
    name: str
    value: "QuantumStateExpr"


@dataclass
class GateApply(Node):
    """apply <gate> → <target>   or   apply <gate>(<q0>, <q1>)"""
    gate: str
    targets: list[str]


@dataclass
class Collapse(Node):
    """collapse <qubit> → <result>"""
    qubit: str
    result: str


@dataclass
class Assert(Node):
    """assert <var> ∈ {values…}  or  assert <var> == <value>"""
    variable: str
    values: list[Any]         # integers / strings / qubit labels
    exact: bool = False       # True when == was used


@dataclass
class LogStmt(Node):
    """log(expr) / print(expr)"""
    expr: Any


@dataclass
class LetBinding(Node):
    """let <name> = <expr>"""
    name: str
    value: Any


@dataclass
class Comment(Node):
    text: str


# ---- Quantum state expressions -------------------------------------------

@dataclass
class QuantumStateExpr:
    pass


@dataclass
class QubitLiteral(QuantumStateExpr):
    """A single |x⟩ state.  inner is '0', '1', '+', '-', 'ψ', etc."""
    inner: str


@dataclass
class Superposition(QuantumStateExpr):
    """α|0⟩ + β|1⟩ — list of (amplitude, QubitLiteral) pairs."""
    terms: list[tuple[float | None, QubitLiteral]]


@dataclass
class StateRef(QuantumStateExpr):
    """Reference to a previously declared state by name."""
    name: str


@dataclass
class TensorProduct(QuantumStateExpr):
    left: QuantumStateExpr
    right: QuantumStateExpr


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

_WHITESPACE_RE = re.compile(r"[ \t\r]+")
_NUMBER_RE = re.compile(r"\d+(\.\d+)?")
_IDENT_RE = re.compile(
    r"[A-Za-z_\u0370-\u03FF\u1F00-\u1FFF]"
    r"[A-Za-z0-9_\u0370-\u03FF\u1F00-\u1FFF]*"
)
_STRING_RE = re.compile(r'"([^"\\]|\\.)*"')


def tokenize(source: str) -> list[Token]:
    """Tokenize a QUBE source string."""
    tokens: list[Token] = []
    pos = 0
    length = len(source)
    line = 1
    col = 1

    def make(tok_type: str, value: Any) -> Token:
        return Token(tok_type, value, line, col)

    while pos < length:
        # whitespace (not newlines)
        m = _WHITESPACE_RE.match(source, pos)
        if m:
            col += m.end() - m.start()
            pos = m.end()
            continue

        ch = source[pos]

        # Newline
        if ch == "\n":
            tokens.append(make(TokenType.NEWLINE, "\n"))
            pos += 1
            line += 1
            col = 1
            continue

        # ASCII arrow ->
        if source[pos:pos+2] == "->":
            tokens.append(make(TokenType.ARROW, "->"))
            col += 2
            pos += 2
            continue

        # == double-equals
        if source[pos:pos+2] == "==":
            tokens.append(make(TokenType.DOUBLE_EQ, "=="))
            col += 2
            pos += 2
            continue

        # Line comments: // or ∴ or ∵
        if source[pos:pos+2] == "//":
            end = source.find("\n", pos)
            if end == -1:
                end = length
            comment_text = source[pos+2:end].strip()
            tokens.append(make(TokenType.COMMENT, comment_text))
            col += end - pos
            pos = end
            continue

        if ch in ("∴", "∵", "⍝"):
            end = source.find("\n", pos)
            if end == -1:
                end = length
            comment_text = source[pos+1:end].strip()
            tokens.append(make(TokenType.COMMENT, comment_text))
            col += end - pos
            pos = end
            continue

        # Strings
        m = _STRING_RE.match(source, pos)
        if m:
            raw = m.group()
            tokens.append(make(TokenType.STRING, raw[1:-1]))
            col += len(raw)
            pos = m.end()
            continue

        # Numbers
        m = _NUMBER_RE.match(source, pos)
        if m:
            tokens.append(make(TokenType.NUMBER, float(m.group())))
            col += m.end() - m.start()
            pos = m.end()
            continue

        # Identifiers / keywords
        m = _IDENT_RE.match(source, pos)
        if m:
            word = m.group()
            tok_type = KEYWORDS.get(word, TokenType.IDENT)
            tokens.append(make(tok_type, word))
            col += len(word)
            pos += len(word)
            continue

        # Pipe → possible qubit literal |x⟩
        if ch == "|":
            pos += 1
            col += 1
            inner = []
            while pos < length and source[pos] not in ("\u27E9", ">", "\n"):
                inner.append(source[pos])
                pos += 1
                col += 1
            if pos < length and source[pos] in ("\u27E9", ">"):
                pos += 1
                col += 1
            inner_str = "".join(inner).strip()
            tokens.append(make(TokenType.QUBIT_INNER, inner_str))
            continue

        # Unicode single-char tokens
        if ch in SINGLE_CHAR_TOKENS:
            tokens.append(make(SINGLE_CHAR_TOKENS[ch], ch))
            pos += 1
            col += 1
            continue

        # Unknown — skip
        pos += 1
        col += 1

    tokens.append(Token(TokenType.EOF, None, line, col))
    return tokens


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        # Filter out pure whitespace newlines (keep only meaningful tokens)
        self._tokens = [t for t in tokens if t.type != TokenType.NEWLINE]
        self._pos = 0

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _check(self, *types: str) -> bool:
        return self._peek().type in types

    def _match(self, *types: str) -> Token | None:
        if self._check(*types):
            return self._advance()
        return None

    def _expect(self, *types: str) -> Token:
        tok = self._peek()
        if tok.type not in types:
            raise ParseError(
                f"Line {tok.line}: expected one of {types!r}, got {tok.type!r} ({tok.value!r})"
            )
        return self._advance()

    # ---- top-level --------------------------------------------------------

    def parse(self) -> QubeProgram:
        stmts: list[Node] = []
        while not self._check(TokenType.EOF):
            s = self._statement()
            if s is not None:
                stmts.append(s)
        return QubeProgram(stmts=stmts)

    def _statement(self) -> Node | None:
        tok = self._peek()

        if tok.type == TokenType.COMMENT:
            self._advance()
            return Comment(text=tok.value)

        if tok.type == TokenType.KW_STATE:
            return self._state_decl()

        if tok.type == TokenType.KW_APPLY:
            return self._gate_apply()

        if tok.type == TokenType.KW_COLLAPSE:
            return self._collapse()

        if tok.type == TokenType.KW_ASSERT:
            return self._assert_stmt()

        if tok.type == TokenType.KW_PRINT:
            return self._log_stmt()

        if tok.type == TokenType.KW_LET:
            return self._let_binding()

        # Unknown — skip token to avoid infinite loop
        self._advance()
        return None

    # ---- state declaration ------------------------------------------------

    def _state_decl(self) -> StateDecl:
        self._expect(TokenType.KW_STATE)
        name = self._expect(TokenType.IDENT).value
        self._expect(TokenType.EQUALS)
        value = self._amplitude_expr()
        return StateDecl(name=name, value=value)

    def _amplitude_expr(self) -> QuantumStateExpr:
        """Parse a superposition expression or a single state/ref."""
        terms: list[tuple[float | None, QubitLiteral]] = []

        amplitude, state = self._amplitude_term()
        if isinstance(state, QubitLiteral):
            terms.append((amplitude, state))
        elif isinstance(state, StateRef):
            if not self._check(TokenType.PLUS, TokenType.MINUS):
                return state
            # Can't superpose state refs — return ref
            return state
        else:
            return state

        while self._check(TokenType.PLUS, TokenType.MINUS):
            sign = 1.0 if self._advance().type == TokenType.PLUS else -1.0
            amp2, st2 = self._amplitude_term()
            if isinstance(st2, QubitLiteral):
                eff_amp = (amp2 if amp2 is not None else 1.0) * sign
                terms.append((eff_amp, st2))

        if len(terms) == 1:
            amp, ql = terms[0]
            if amp is None or amp == 1.0:
                return ql
        return Superposition(terms=terms)

    def _amplitude_term(self) -> tuple[float | None, QuantumStateExpr]:
        """Returns (amplitude_or_None, state_expr)."""
        amplitude: float | None = None

        if self._check(TokenType.NUMBER):
            amplitude = self._advance().value

        if self._check(TokenType.QUBIT_INNER):
            inner = self._advance().value
            return amplitude, QubitLiteral(inner=inner)

        if self._check(TokenType.IDENT):
            name = self._advance().value
            return amplitude, StateRef(name=name)

        raise ParseError(f"Line {self._peek().line}: expected qubit literal or identifier in state expression")

    # ---- gate application -------------------------------------------------

    def _gate_apply(self) -> GateApply:
        self._expect(TokenType.KW_APPLY)
        gate_tok = self._expect(TokenType.IDENT)
        gate = gate_tok.value

        # Optional rotation angle inside parentheses for Rx/Ry/Rz BEFORE arrow
        # e.g. apply Rx(1.5708) → q   — the angle is embedded in gate name for simplicity
        if self._check(TokenType.LPAREN) and gate not in TWO_QUBIT_GATES:
            # Peek ahead: if next is a number this is a rotation angle
            self._advance()  # consume (
            if self._check(TokenType.NUMBER):
                angle = self._advance().value
                gate = f"{gate}({angle})"
                self._expect(TokenType.RPAREN)

        # Two-qubit gate: apply CNOT(q0, q1) or apply CNOT → q0, q1
        if self._check(TokenType.LPAREN):
            self._advance()  # consume (
            targets = [self._expect(TokenType.IDENT).value]
            while self._match(TokenType.COMMA):
                targets.append(self._expect(TokenType.IDENT).value)
            self._expect(TokenType.RPAREN)
            return GateApply(gate=gate, targets=targets)

        # Single-qubit: apply H → q
        self._expect(TokenType.ARROW)
        # Accept single or comma-separated targets after arrow
        targets = [self._expect(TokenType.IDENT).value]
        while self._match(TokenType.COMMA):
            targets.append(self._expect(TokenType.IDENT).value)
        return GateApply(gate=gate, targets=targets)

    # ---- collapse ---------------------------------------------------------

    def _collapse(self) -> Collapse:
        self._expect(TokenType.KW_COLLAPSE)
        qubit = self._expect(TokenType.IDENT).value
        self._expect(TokenType.ARROW)
        result = self._expect(TokenType.IDENT).value
        return Collapse(qubit=qubit, result=result)

    # ---- assert -----------------------------------------------------------

    def _assert_stmt(self) -> Assert:
        self._expect(TokenType.KW_ASSERT)
        variable = self._expect(TokenType.IDENT).value

        if self._match(TokenType.DOUBLE_EQ):
            value = self._assert_value()
            return Assert(variable=variable, values=[value], exact=True)

        self._expect(TokenType.MEMBER)
        self._expect(TokenType.LBRACE)
        values = [self._assert_value()]
        while self._match(TokenType.COMMA):
            values.append(self._assert_value())
        self._expect(TokenType.RBRACE)
        return Assert(variable=variable, values=values)

    def _assert_value(self) -> Any:
        if self._check(TokenType.NUMBER):
            return self._advance().value
        if self._check(TokenType.QUBIT_INNER):
            return f"|{self._advance().value}⟩"
        if self._check(TokenType.IDENT):
            return self._advance().value
        raise ParseError(f"Line {self._peek().line}: expected assert value")

    # ---- log --------------------------------------------------------------

    def _log_stmt(self) -> LogStmt:
        self._expect(TokenType.KW_PRINT)
        self._expect(TokenType.LPAREN)
        expr = self._simple_expr()
        self._expect(TokenType.RPAREN)
        return LogStmt(expr=expr)

    def _simple_expr(self) -> Any:
        if self._check(TokenType.IDENT):
            return self._advance().value
        if self._check(TokenType.NUMBER):
            return self._advance().value
        if self._check(TokenType.STRING):
            return self._advance().value
        if self._check(TokenType.QUBIT_INNER):
            return f"|{self._advance().value}⟩"
        return None

    # ---- let binding ------------------------------------------------------

    def _let_binding(self) -> LetBinding:
        self._expect(TokenType.KW_LET)
        name = self._expect(TokenType.IDENT).value
        self._expect(TokenType.EQUALS)
        value = self._simple_expr()
        return LetBinding(name=name, value=value)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(source: str) -> QubeProgram:
    """Parse QUBE *source* into a :class:`QubeProgram` AST."""
    tokens = tokenize(source)
    return Parser(tokens).parse()

