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


from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .qube_syntax import GLYPH_TOKENS, TokenType


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------

@dataclass
class Token:
    type: str
    value: Any
    pos: int = 0

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r})"


# ---------------------------------------------------------------------------
# AST nodes
# ---------------------------------------------------------------------------

@dataclass
class Node:
    pass


@dataclass
class Program(Node):
    statements: list[Node] = field(default_factory=list)


@dataclass
class Binding(Node):
    """λ name ≔ value"""
    name: str
    value: Node


@dataclass
class Entanglement(Node):
    """left ⊗ right"""
    left: Node
    right: Node


@dataclass
class Superposition(Node):
    """left ⊕ right"""
    left: Node
    right: Node


@dataclass
class Collapse(Node):
    """↯ state"""
    state: Node


@dataclass
class Evolution(Node):
    """⟳ expr"""
    body: Node


@dataclass
class GlyphLock(Node):
    """◈ expr"""
    expr: Node


@dataclass
class FlowPipe(Node):
    """source ↝ target"""
    source: Node
    target: Node


@dataclass
class QuantumState(Node):
    """|content⟩"""
    content: Node


@dataclass
class ConstructorCall(Node):
    """Æ(args...)"""
    args: list[Node] = field(default_factory=list)


@dataclass
class Infinity(Node):
    """∞"""


@dataclass
class Bottom(Node):
    """⊥"""


@dataclass
class Psi(Node):
    """ψ"""


@dataclass
class EntropyCredit(Node):
    """⧖ amount"""
    amount: Node


@dataclass
class Consume(Node):
    """⟜ expr"""
    expr: Node


@dataclass
class Yields(Node):
    """left ⊢ right  (used as infix in expressions — mapped to call site)"""
    context: Node
    result: Node


@dataclass
class Join(Node):
    """left ⋈ right"""
    left: Node
    right: Node


@dataclass
class Call(Node):
    """name(args...)"""
    name: str
    args: list[Node] = field(default_factory=list)


@dataclass
class Identifier(Node):
    name: str


@dataclass
class Number(Node):
    value: float


@dataclass
class StringLiteral(Node):
    value: str


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

_WHITESPACE_RE = re.compile(r"[ \t]+")
_NUMBER_RE = re.compile(r"-?\d+(\.\d+)?")
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_STRING_RE = re.compile(r'"([^"\\]|\\.)*"')
_COMMENT_RE = re.compile(r"#[^\n]*")


def tokenize(source: str) -> list[Token]:
    """Convert a QUBE source string into a list of tokens."""
    tokens: list[Token] = []
    pos = 0
    length = len(source)

    while pos < length:
        # Skip comments
        m = _COMMENT_RE.match(source, pos)
        if m:
            pos = m.end()
            continue

        # Skip whitespace (not newlines)
        m = _WHITESPACE_RE.match(source, pos)
        if m:
            pos = m.end()
            continue

        # Newlines
        if source[pos] == "\n":
            tokens.append(Token(TokenType.NEWLINE, "\n", pos))
            pos += 1
            continue

        ch = source[pos]

        # Strings
        m = _STRING_RE.match(source, pos)
        if m:
            raw = m.group()
            tokens.append(Token(TokenType.STRING, raw[1:-1].replace('\\"', '"'), pos))
            pos = m.end()
            continue

        # Numbers
        m = _NUMBER_RE.match(source, pos)
        if m:
            val = m.group()
            tokens.append(Token(TokenType.NUMBER, float(val), pos))
            pos = m.end()
            continue

        # Glyph single-char tokens (including multi-byte unicode)
        if ch in GLYPH_TOKENS:
            tokens.append(Token(GLYPH_TOKENS[ch], ch, pos))
            pos += 1
            continue

        # Identifiers (ASCII)
        m = _IDENT_RE.match(source, pos)
        if m:
            tokens.append(Token(TokenType.IDENT, m.group(), pos))
            pos = m.end()
            continue

        raise SyntaxError(f"Unexpected character {ch!r} at position {pos}")

    tokens.append(Token(TokenType.EOF, None, pos))
    return tokens


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = [t for t in tokens if t.type != TokenType.NEWLINE]
        self._pos = 0

    # ---- helpers -----------------------------------------------------------

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _check(self, *types: str) -> bool:
        return self._peek().type in types

    def _expect(self, *types: str) -> Token:
        tok = self._peek()
        if tok.type not in types:
            raise ParseError(
                f"Expected one of {types!r} but got {tok.type!r} ({tok.value!r})"
            )
        return self._advance()

    def _match(self, *types: str) -> Token | None:
        if self._check(*types):
            return self._advance()
        return None

    # ---- grammar -----------------------------------------------------------

    def parse(self) -> Program:
        stmts: list[Node] = []
        while not self._check(TokenType.EOF):
            stmts.append(self._statement())
        return Program(statements=stmts)

    def _statement(self) -> Node:
        if self._check(TokenType.LAMBDA):
            return self._binding()
        return self._expression()

    def _binding(self) -> Binding:
        self._expect(TokenType.LAMBDA)
        name_tok = self._expect(TokenType.IDENT)
        self._expect(TokenType.ASSIGN)
        value = self._expression()
        return Binding(name=name_tok.value, value=value)

    def _expression(self) -> Node:
        return self._pipe_expr()

    def _pipe_expr(self) -> Node:
        left = self._tensor_expr()
        while self._match(TokenType.FLOW):
            right = self._tensor_expr()
            left = FlowPipe(source=left, target=right)
        return left

    def _tensor_expr(self) -> Node:
        left = self._super_expr()
        while True:
            if self._match(TokenType.ENTANGLE):
                right = self._super_expr()
                left = Entanglement(left=left, right=right)
            elif self._match(TokenType.YIELDS):
                right = self._super_expr()
                left = Yields(context=left, result=right)
            elif self._match(TokenType.JOIN):
                right = self._super_expr()
                left = Join(left=left, right=right)
            else:
                break
        return left

    def _super_expr(self) -> Node:
        left = self._unary_expr()
        while self._match(TokenType.SUPERPOSE):
            right = self._unary_expr()
            left = Superposition(left=left, right=right)
        return left

    def _unary_expr(self) -> Node:
        if self._match(TokenType.COLLAPSE):
            return Collapse(state=self._unary_expr())
        if self._match(TokenType.EVOLVE):
            return Evolution(body=self._unary_expr())
        if self._match(TokenType.GLYPH_LOCK):
            return GlyphLock(expr=self._unary_expr())
        if self._match(TokenType.ENTROPY):
            return EntropyCredit(amount=self._unary_expr())
        if self._match(TokenType.CONSUME):
            return Consume(expr=self._unary_expr())
        return self._primary()

    def _primary(self) -> Node:
        tok = self._peek()

        # |expr⟩
        if self._match(TokenType.STATE_OPEN):
            content = self._expression()
            self._expect(TokenType.STATE_CLOSE)
            return QuantumState(content=content)

        # Æ(args)
        if self._match(TokenType.CONSTRUCTOR):
            self._expect(TokenType.LPAREN)
            args = self._arg_list()
            self._expect(TokenType.RPAREN)
            return ConstructorCall(args=args)

        # ∞
        if self._match(TokenType.INFINITY):
            return Infinity()

        # ⊥
        if self._match(TokenType.BOTTOM):
            return Bottom()

        # ψ
        if self._match(TokenType.PSI):
            return Psi()

        # Identifier or call
        if self._check(TokenType.IDENT):
            name = self._advance().value
            if self._match(TokenType.LPAREN):
                args = self._arg_list()
                self._expect(TokenType.RPAREN)
                return Call(name=name, args=args)
            return Identifier(name=name)

        # Number
        if self._check(TokenType.NUMBER):
            return Number(value=self._advance().value)

        # String
        if self._check(TokenType.STRING):
            return StringLiteral(value=self._advance().value)

        # Grouping
        if self._match(TokenType.LPAREN):
            expr = self._expression()
            self._expect(TokenType.RPAREN)
            return expr

        raise ParseError(f"Unexpected token {tok!r}")

    def _arg_list(self) -> list[Node]:
        args: list[Node] = []
        if self._check(TokenType.RPAREN):
            return args
        args.append(self._expression())
        while self._match(TokenType.COMMA):
            args.append(self._expression())
        return args


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(source: str) -> Program:
    """Parse *source* into a QUBE :class:`Program` AST."""
    tokens = tokenize(source)
    return Parser(tokens).parse()
