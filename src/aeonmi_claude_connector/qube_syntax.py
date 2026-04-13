"""Aeonmi / QUBE syntax definitions.

Ground truth sourced from https://github.com/Aeonmi-Aysa/aeonmi:
  docs/grammar_qube.md
  docs/QUBE_SPEC.md
  docs/LANGUAGE_SPEC_CURRENT.md
  docs/glyph_algebra.md
  src/qube/lexer.rs
  src/qube/ast.rs
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# QUBE (.qube) token types — mirrors src/qube/lexer.rs QubeTok
# ---------------------------------------------------------------------------

class TokenType:
    # Keywords
    KW_STATE    = "KW_STATE"     # state
    KW_APPLY    = "KW_APPLY"     # apply
    KW_COLLAPSE = "KW_COLLAPSE"  # collapse
    KW_ASSERT   = "KW_ASSERT"    # assert
    KW_PRINT    = "KW_PRINT"     # print / log
    KW_LET      = "KW_LET"       # let

    # Operators
    ARROW      = "ARROW"      # →  (also plain ASCII ->)
    MEMBER     = "MEMBER"     # ∈
    TENSOR_OP  = "TENSOR_OP"  # ⊗
    PLUS       = "PLUS"       # +
    MINUS      = "MINUS"      # -
    STAR       = "STAR"       # *
    SLASH      = "SLASH"      # /
    EQUALS     = "EQUALS"     # =
    DOUBLE_EQ  = "DOUBLE_EQ"  # ==

    # Delimiters
    PIPE        = "PIPE"        # |  (start of qubit literal)
    R_ANGLE     = "R_ANGLE"     # ⟩  (also accepts ASCII >)
    LBRACE      = "LBRACE"      # {
    RBRACE      = "RBRACE"      # }
    LPAREN      = "LPAREN"      # (
    RPAREN      = "RPAREN"      # )
    COMMA       = "COMMA"       # ,

    # Literals
    NUMBER      = "NUMBER"
    IDENT       = "IDENT"
    QUBIT_INNER = "QUBIT_INNER"  # content between | and ⟩
    STRING      = "STRING"

    # Structure
    COMMENT = "COMMENT"
    NEWLINE = "NEWLINE"
    EOF     = "EOF"


# Keyword map
KEYWORDS: dict[str, str] = {
    "state":    TokenType.KW_STATE,
    "apply":    TokenType.KW_APPLY,
    "collapse": TokenType.KW_COLLAPSE,
    "assert":   TokenType.KW_ASSERT,
    "print":    TokenType.KW_PRINT,
    "log":      TokenType.KW_PRINT,
    "let":      TokenType.KW_LET,
}

# Single-character Unicode → token type
SINGLE_CHAR_TOKENS: dict[str, str] = {
    "→": TokenType.ARROW,
    "∈": TokenType.MEMBER,
    "⊗": TokenType.TENSOR_OP,
    "⟩": TokenType.R_ANGLE,
    ">": TokenType.R_ANGLE,   # ASCII fallback
    "|": TokenType.PIPE,
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    ",": TokenType.COMMA,
    "=": TokenType.EQUALS,
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
}

# Qubit inner literals that start qubit literal parsing (after |)
QUBIT_STARTERS: frozenset[str] = frozenset("01+−-ψφΦΩ")

# ---------------------------------------------------------------------------
# Quantum gate catalogue — mirrors src/qube/ast.rs QuantumGate
# ---------------------------------------------------------------------------

GATES: dict[str, str] = {
    "H":    "Hadamard — creates equal superposition from |0⟩",
    "X":    "Pauli-X — bit flip",
    "Y":    "Pauli-Y — bit + phase flip",
    "Z":    "Pauli-Z — phase flip",
    "S":    "Phase gate (π/2 rotation around Z)",
    "T":    "T gate (π/4 rotation around Z)",
    "Rx":   "Rotation around X axis (angle in radians as float arg)",
    "Ry":   "Rotation around Y axis (angle in radians)",
    "Rz":   "Rotation around Z axis (angle in radians)",
    "CNOT": "Controlled-NOT — 2-qubit: first arg is control, second is target",
    "CX":   "Alias for CNOT",
    "CZ":   "Controlled-Z — 2-qubit",
    "SWAP": "Swap — exchanges two qubit states",
}

TWO_QUBIT_GATES: frozenset[str] = frozenset({"CNOT", "CX", "CZ", "SWAP"})

# Unitary matrices for 1-qubit gates (2x2, row-major, complex as (re, im) pairs)
import cmath
import math

_I = complex(0, 1)
_S2 = math.sqrt(0.5)

GATE_MATRICES: dict[str, list[list[complex]]] = {
    "H":  [[_S2, _S2], [_S2, -_S2]],
    "X":  [[0, 1], [1, 0]],
    "Y":  [[0, -_I], [_I, 0]],
    "Z":  [[1, 0], [0, -1]],
    "S":  [[1, 0], [0, _I]],
    "T":  [[1, 0], [0, cmath.exp(_I * math.pi / 4)]],
}

# ---------------------------------------------------------------------------
# Aeonmi .ai quantum operators — mirrors LANGUAGE_SPEC_CURRENT.md §4
# ---------------------------------------------------------------------------

AI_QUANTUM_OPERATORS: dict[str, str] = {
    "←":  "Quantum bind — classical value into quantum context  (e.g. ⟨x⟩ ← 42)",
    "∈":  "Quantum membership — bind to a superposition  (e.g. ⟨psi⟩ ∈ |0⟩ + |1⟩)",
    "⊗":  "Tensor product — quantum tensor of two states",
    "≈":  "Approximation — probabilistic equality  (e.g. ⟨q⟩ ≈ 0.707)",
    "⊕":  "Quantum XOR / superposition merge",
    "⊖":  "Quantum OR / probability branch  (⊖ cond ≈ 0.8 ⇒ { })",
    "⊄":  "Quantum NOT",
    "∇":  "Gradient / gradient-descent operator",
    "⪰":  "Quantum GEQ (≥ with probability)",
    "⪯":  "Quantum LEQ (≤ with probability)",
    "⇒":  "Implies / then branch  (used in probability-aware control flow)",
    "⟲":  "Quantum loop with decoherence condition",
    "◊":  "Quantum modulo with superposition",
    "∴":  "Therefore — line comment",
    "∵":  "Because — reason comment",
    "⍝":  "APL-style line comment (also used in .ai files)",
    "※":  "Note comment",
}

# ---------------------------------------------------------------------------
# Glyph algebra primitives — mirrors docs/glyph_algebra.md
# ---------------------------------------------------------------------------

GLYPH_ALGEBRA: dict[str, str] = {
    "⧉":  "Array Genesis — symbolic dense collection literal  (e.g. ⧉0.707‥0‥0‥0.707⧉)",
    "‥":  "Separator inside ⧉…⧉ array literals",
    "⟨⟩": "Slice / index / projection  (e.g. ⟨arr⟩⟦i⟧ or ⟨x⟩ ← 42)",
    "…":  "Spread / expansion operator",
    "⊗":  "Tensor combination  (shared with quantum operator)",
    "↦":  "Symbolic binding / projection  (e.g. ψ ↦ bell ⊗ bell)",
}

# ---------------------------------------------------------------------------
# QUBE grammar reference (human-readable)
# ---------------------------------------------------------------------------

QUBE_GRAMMAR_REFERENCE = """\
QUBE Grammar Reference (Aeonmi-Aysa/aeonmi)
============================================
Source: docs/grammar_qube.md + docs/QUBE_SPEC.md

EBNF:

program        ::= statement* EOF

statement      ::= state_decl
                 | gate_apply
                 | collapse
                 | assert_stmt
                 | log_stmt
                 | let_binding
                 | comment

state_decl     ::= "state" IDENT "=" amplitude_expr
                 | "state" IDENT "=" qubit_literal

amplitude_expr ::= amplitude_term (("+" | "-") amplitude_term)*
amplitude_term ::= NUMBER? qubit_literal
                 | IDENT

qubit_literal  ::= "|" (IDENT | NUMBER | "+" | "-") "⟩"
                 | "|" (IDENT | NUMBER | "+" | "-") ">"   (* ASCII fallback *)

gate_apply     ::= "apply" gate_name "→" IDENT
                 | "apply" gate_name "(" IDENT ("," IDENT)* ")"

gate_name      ::= "H" | "X" | "Y" | "Z" | "CNOT" | "CX"
                 | "T" | "S" | "Rx" | "Ry" | "Rz"
                 | "CZ" | "SWAP"
                 | IDENT   (* user-defined gate *)

collapse       ::= "collapse" IDENT "→" IDENT

assert_stmt    ::= "assert" IDENT "∈" "{" assert_value ("," assert_value)* "}"
                 | "assert" IDENT "==" assert_value

assert_value   ::= NUMBER | qubit_literal | IDENT

log_stmt       ::= ("log" | "print") "(" expr ")"

let_binding    ::= "let" IDENT "=" expr

comment        ::= "//" ANY* NEWLINE
                 | "∴" ANY* NEWLINE      (* therefore *)
                 | "∵" ANY* NEWLINE      (* because *)

expr           ::= IDENT | NUMBER | STRING | qubit_literal

IDENT          ::= [a-zA-Z_α-ωΑ-Ω] [a-zA-Z0-9_α-ωΑ-Ω]*
NUMBER         ::= [0-9]+ ("." [0-9]+)?
STRING         ::= '"' [^"]* '"'

CLI:
  aeonmi qube run <file.qube>      execute circuit
  aeonmi qube check <file.qube>    parse + type-check
  aeonmi qube diagram <file.qube>  ASCII circuit diagram
"""

# ---------------------------------------------------------------------------
# Aeonmi .ai language reference (summary)
# ---------------------------------------------------------------------------

AI_LANGUAGE_REFERENCE = """\
Aeonmi Language (.ai) — Quick Reference
========================================
Source: docs/LANGUAGE_SPEC_CURRENT.md

Variables:
  let x = 42;
  const PI = 3.14159;

Functions:
  function add(a, b) { return a + b; }
  quantum function flip() { qubit q; superpose(q); return measure(q); }
  async function fetch(url) { return await http_get(url); }

Control flow:
  if x > 0 { … } else { … }
  while i < 10 { i = i + 1; }
  for (let i = 0; i < n; i = i + 1) { … }
  for item in collection { … }
  match value { 42 => { … }, * => { … } }

Quantum primitives:
  qubit q;
  superpose(q);           // Hadamard gate
  let bit = measure(q);   // collapse → 0 or 1
  entangle(q1, q2);       // entangle metadata
  apply_gate(q, H);       // apply gate constant

Qubit literals:  |0⟩  |1⟩  |+⟩  |-⟩  |ψ⟩

Quantum-native Unicode declarations:
  ⟨x⟩ ← 42                    // classical bind
  ⟨psi⟩ ∈ |0⟩ + |1⟩           // superposition bind
  ⟨tensor⟩ ⊗ value              // tensor bind

Probability-aware control flow:
  ⊖ condition ≈ 0.8 ⇒ { }      // 80 % branch
  ⟲ condition ⪰ 0.5 ⇒ { }      // quantum loop

Glyph algebra:
  bell ← ⧉0.707‥0‥0‥0.707⧉
  ψ ↦ bell ⊗ bell

Comments:  // …   ∴ …   ∵ …   ⍝ …   ※ …

CLI:
  aeonmi run <file.ai>       compile to JS + execute
  aeonmi exec <file.ai>      native VM
  aeonmi repl                interactive shell
"""

# ---------------------------------------------------------------------------
# Built-in QUBE example circuits (from docs)
# ---------------------------------------------------------------------------

QUBE_EXAMPLES = [
    {
        "name": "Pure State — X Gate",
        "description": "Flip |0⟩ to |1⟩ with a Pauli-X gate, then measure.",
        "code": (
            "state q = |0⟩\n"
            "apply X → q\n"
            "collapse q → r\n"
            "assert r == 1\n"
            "log(r)"
        ),
    },
    {
        "name": "Superposition",
        "description": "Create equal superposition with Hadamard; measure gives 0 or 1.",
        "code": (
            "state ψ = 0.707|0⟩ + 0.707|1⟩\n"
            "collapse ψ → result\n"
            "assert result ∈ {0, 1}\n"
            "log(result)"
        ),
    },
    {
        "name": "Bell State",
        "description": "Maximally entangled two-qubit Bell pair.",
        "code": (
            "∴ Bell state: maximally entangled pair\n"
            "state q0 = |0⟩\n"
            "state q1 = |0⟩\n"
            "apply H → q0\n"
            "apply CNOT(q0, q1)\n"
            "collapse q0 → r0\n"
            "collapse q1 → r1\n"
            "∵ Bell pair always collapses to the same bit\n"
            "assert r0 ∈ {0, 1}\n"
            "assert r1 ∈ {0, 1}\n"
            "log(r0)\n"
            "log(r1)"
        ),
    },
    {
        "name": "GHZ State",
        "description": "Three-qubit Greenberger-Horne-Zeilinger entangled state.",
        "code": (
            "state a = |0⟩\n"
            "state b = |0⟩\n"
            "state c = |0⟩\n"
            "apply H → a\n"
            "apply CNOT(a, b)\n"
            "apply CNOT(a, c)\n"
            "collapse a → ra\n"
            "collapse b → rb\n"
            "collapse c → rc\n"
            "assert ra ∈ {0, 1}\n"
            "assert rb ∈ {0, 1}\n"
            "assert rc ∈ {0, 1}\n"
            "log(ra)\n"
            "log(rb)\n"
            "log(rc)"
        ),
    },
    {
        "name": "Phase Kickback (Z Gate)",
        "description": "Apply Z to a |+⟩ state to get |−⟩.",
        "code": (
            "state q = |+⟩\n"
            "apply Z → q\n"
            "collapse q → r\n"
            "assert r ∈ {0, 1}\n"
            "log(r)"
        ),
    },
]

# ---------------------------------------------------------------------------
# Built-in Aeonmi .ai example programs
# ---------------------------------------------------------------------------

AI_EXAMPLES = [
    {
        "name": "Hello World",
        "description": "Minimal Aeonmi program.",
        "code": 'log(42);',
    },
    {
        "name": "Quantum Coin Flip",
        "description": "Single qubit in superposition, measured to 0 or 1.",
        "code": (
            "quantum function flip_coin() {\n"
            "    qubit q;\n"
            "    superpose(q);\n"
            "    let result = measure(q);\n"
            "    if result == 0 {\n"
            '        log("Heads");\n'
            "    } else {\n"
            '        log("Tails");\n'
            "    }\n"
            "    return result;\n"
            "}\n"
            "flip_coin();"
        ),
    },
    {
        "name": "Quantum-Native Variable",
        "description": "Glyph-algebra style superposition binding.",
        "code": (
            "⟨psi⟩ ∈ |0⟩ + |1⟩\n"
            "∴ psi is now in equal superposition"
        ),
    },
    {
        "name": "Bell State in .ai",
        "description": "Two-qubit Bell pair using apply_gate.",
        "code": (
            "quantum function bell_state() {\n"
            "    qubit q1;\n"
            "    qubit q2;\n"
            "    superpose(q1);\n"
            "    apply_gate(q1, q2, CNOT);\n"
            "    let r1 = measure(q1);\n"
            "    let r2 = measure(q2);\n"
            "    log(r1);\n"
            "    log(r2);\n"
            "}\n"
            "bell_state();"
        ),
    },
    {
        "name": "Glyph Algebra Array",
        "description": "Dense symbolic array using Array Genesis glyph.",
        "code": (
            "∴ Bell state vector using glyph algebra\n"
            "bell ← ⧉0.707‥0‥0‥0.707⧉\n"
            "ψ ↦ bell ⊗ bell"
        ),
    },
]
