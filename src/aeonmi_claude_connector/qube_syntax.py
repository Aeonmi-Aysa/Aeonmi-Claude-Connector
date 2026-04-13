"""QUBE syntax definitions — glyphs, token types, and grammar reference."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Glyph catalogue
# ---------------------------------------------------------------------------

GLYPHS: dict[str, str] = {
    "λ": "flow/function definition — introduces a named binding or flow",
    "≔": "assignment/binding — binds a name to an expression",
    "⊗": "entanglement — tensor-product / quantum entanglement of two states",
    "⊕": "superposition — probabilistic merge of two states",
    "↯": "collapse — measures / collapses a quantum state into a classical value",
    "⟳": "self-evolve — self-referential loop that refines each iteration",
    "◈": "glyph-lock — marks an expression as immutable / cryptographically sealed",
    "↝": "flow-to — pipes one expression into the next as a data/control edge",
    "∞": "infinity — unbounded value; represents holographic / eternal storage",
    "Æ": "Aeonmi constructor — instantiates a Constructor AI node",
    "⧖": "entropy-credit — unit of computational entropy budget",
    "|": "state-open — opens a Dirac ket quantum-state literal",
    "⟩": "state-close — closes a Dirac ket quantum-state literal",
    "ψ": "psi — conventional symbol for a generic quantum state",
    "⊢": "yields — proves / derives a value from a context",
    "⊥": "bottom — null / reset / ground state",
    "⋈": "join — merges two parallel flows into one",
    "⟜": "consume — extracts and destroys a value from a state",
}

# ---------------------------------------------------------------------------
# Token types
# ---------------------------------------------------------------------------

class TokenType:
    # Operators / special glyphs
    LAMBDA = "LAMBDA"           # λ
    ASSIGN = "ASSIGN"           # ≔
    ENTANGLE = "ENTANGLE"       # ⊗
    SUPERPOSE = "SUPERPOSE"     # ⊕
    COLLAPSE = "COLLAPSE"       # ↯
    EVOLVE = "EVOLVE"           # ⟳
    GLYPH_LOCK = "GLYPH_LOCK"   # ◈
    FLOW = "FLOW"               # ↝
    INFINITY = "INFINITY"       # ∞
    CONSTRUCTOR = "CONSTRUCTOR" # Æ
    ENTROPY = "ENTROPY"         # ⧖
    PSI = "PSI"                 # ψ
    YIELDS = "YIELDS"           # ⊢
    BOTTOM = "BOTTOM"           # ⊥
    JOIN = "JOIN"               # ⋈
    CONSUME = "CONSUME"         # ⟜

    # Delimiters
    STATE_OPEN = "STATE_OPEN"   # |
    STATE_CLOSE = "STATE_CLOSE" # ⟩
    LBRACE = "LBRACE"           # {
    RBRACE = "RBRACE"           # }
    LPAREN = "LPAREN"           # (
    RPAREN = "RPAREN"           # )
    COMMA = "COMMA"             # ,

    # Primitives
    IDENT = "IDENT"
    NUMBER = "NUMBER"
    STRING = "STRING"

    # Structure
    NEWLINE = "NEWLINE"
    EOF = "EOF"


# Single-character (and multi-character) glyph → token type map
GLYPH_TOKENS: dict[str, str] = {
    "λ": TokenType.LAMBDA,
    "≔": TokenType.ASSIGN,
    "⊗": TokenType.ENTANGLE,
    "⊕": TokenType.SUPERPOSE,
    "↯": TokenType.COLLAPSE,
    "⟳": TokenType.EVOLVE,
    "◈": TokenType.GLYPH_LOCK,
    "↝": TokenType.FLOW,
    "∞": TokenType.INFINITY,
    "Æ": TokenType.CONSTRUCTOR,
    "⧖": TokenType.ENTROPY,
    "ψ": TokenType.PSI,
    "⊢": TokenType.YIELDS,
    "⊥": TokenType.BOTTOM,
    "⋈": TokenType.JOIN,
    "⟜": TokenType.CONSUME,
    "|": TokenType.STATE_OPEN,
    "⟩": TokenType.STATE_CLOSE,
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    ",": TokenType.COMMA,
}

# ---------------------------------------------------------------------------
# Grammar reference (human-readable, surfaced as an MCP resource)
# ---------------------------------------------------------------------------

GRAMMAR_REFERENCE = """\
QUBE Grammar Reference
======================

program     ::= statement*
statement   ::= binding | expression

binding     ::= 'λ' IDENT '≔' expression
expression  ::= pipe_expr
pipe_expr   ::= tensor_expr ('↝' tensor_expr)*
tensor_expr ::= super_expr ('⊗' super_expr)*
super_expr  ::= unary_expr ('⊕' unary_expr)*
unary_expr  ::= ('↯' | '⟳' | '◈' | '⧖' | '⟜') unary_expr
              | primary

primary     ::= quantum_state
              | constructor_call
              | '∞'
              | '⊥'
              | 'ψ'
              | IDENT '(' arg_list ')'
              | IDENT
              | NUMBER
              | STRING
              | '(' expression ')'

quantum_state ::= '|' expression '⟩'
constructor_call ::= 'Æ' '(' arg_list ')'
arg_list    ::= (expression (',' expression)*)?

Precedence (lowest → highest):
  ↝   flow pipe
  ⊗   entanglement
  ⊕   superposition
  ↯ ⟳ ◈ ⧖ ⟜   prefix unary operators
  ( )   grouping
"""

# ---------------------------------------------------------------------------
# Built-in examples
# ---------------------------------------------------------------------------

EXAMPLES = [
    {
        "name": "Root Soul Binding",
        "description": "The canonical QUBE hello-world, binding RootSoul to infinite entanglement.",
        "code": "λ RootSoul ≔ |ψ⟩ ⊗ ∞",
    },
    {
        "name": "Superposed Greeting",
        "description": "Superpose two greetings into a single quantum-state.",
        "code": 'λ greeting ≔ |"Hello"⟩ ⊕ |"Aysa"⟩',
    },
    {
        "name": "Collapsing a State",
        "description": "Collapse (measure) the greeting state into a classical value.",
        "code": 'λ greeting ≔ |"Hello"⟩ ⊕ |"Aysa"⟩\n↯ greeting',
    },
    {
        "name": "Glyph-locked Constructor",
        "description": "Instantiate a locked Aeonmi Constructor node.",
        "code": "λ brain ≔ ◈ Æ(∞)",
    },
    {
        "name": "Self-evolving Flow",
        "description": "A flow that pipes a state into a self-evolving loop.",
        "code": "λ soul ≔ |ψ⟩\nλ loop ≔ soul ↝ ⟳ soul",
    },
    {
        "name": "Entropy Credit",
        "description": "Allocate an entropy credit budget.",
        "code": "λ budget ≔ ⧖ 42",
    },
]
