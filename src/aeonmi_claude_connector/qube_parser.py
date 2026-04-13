"""QUBE lexer and recursive-descent parser.

Produces an AST that can be interpreted by qube_executor.py.
"""

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
