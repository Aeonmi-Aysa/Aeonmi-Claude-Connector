"""Aeonmi Claude Connector — MCP server.

Exposes tools and resources for working with QUBE (.qube) and
Aeonmi (.ai) quantum programming languages.

Tools:
  qube_run, qube_check, qube_diagram, qube_explain, qube_generate,
  aeonmi_explain, aeonmi_generate, aeonmi_list_keywords,
  mother_help, cli_help

Resources:
  aeonmi://docs/qube-grammar, aeonmi://docs/language-spec,
  aeonmi://docs/glyph-algebra, aeonmi://docs/mother-guide,
  aeonmi://docs/cli-reference, aeonmi://examples/qube,
  aeonmi://examples/ai, aeonmi://snippets/qube, aeonmi://snippets/ai
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .qube_executor import diagram as _build_diagram
from .qube_executor import execute as _execute
from .qube_parser import ParseError, parse as _parse
from .qube_syntax import (
    AI_EXAMPLES,
    AI_LANGUAGE_REFERENCE,
    AI_QUANTUM_OPERATORS,
    GATES,
    GLYPH_ALGEBRA,
    QUBE_EXAMPLES,
    QUBE_GRAMMAR_REFERENCE,
    TWO_QUBIT_GATES,
)

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------

mcp = FastMCP("aeonmi-claude-connector")

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_GATE_EXPLANATIONS: dict[str, dict[str, Any]] = {
    "H": {
        "explanation": (
            "The Hadamard gate (H) creates an equal superposition from a basis state. "
            "Applying H to |0⟩ produces (|0⟩ + |1⟩)/√2, i.e. the |+⟩ state. "
            "It is the most common gate for initialising quantum algorithms."
        ),
        "examples": [
            "state q = |0⟩\napply H -> q\ncollapse q -> r\nlog(r)",
            "state ψ = |0⟩\napply H -> ψ\ncollapse ψ -> bit\nassert bit ∈ {0, 1}",
        ],
    },
    "X": {
        "explanation": (
            "The Pauli-X gate (X) is the quantum bit-flip. "
            "It maps |0⟩ → |1⟩ and |1⟩ → |0⟩, analogous to a classical NOT gate."
        ),
        "examples": [
            "state q = |0⟩\napply X -> q\ncollapse q -> r\nassert r == 1\nlog(r)",
        ],
    },
    "Y": {
        "explanation": (
            "The Pauli-Y gate applies both a bit flip and a phase flip: "
            "|0⟩ → i|1⟩, |1⟩ → -i|0⟩."
        ),
        "examples": ["state q = |0⟩\napply Y -> q\ncollapse q -> r\nlog(r)"],
    },
    "Z": {
        "explanation": (
            "The Pauli-Z gate applies a phase flip: |0⟩ → |0⟩, |1⟩ → -|1⟩. "
            "It leaves the computational basis intact but flips the relative phase."
        ),
        "examples": [
            "state q = |+⟩\napply Z -> q\ncollapse q -> r\nlog(r)",
        ],
    },
    "S": {
        "explanation": (
            "The S gate (phase gate) rotates the |1⟩ component by π/2: "
            "|0⟩ → |0⟩, |1⟩ → i|1⟩. It is the square root of the Z gate."
        ),
        "examples": ["state q = |+⟩\napply S -> q\ncollapse q -> r\nlog(r)"],
    },
    "T": {
        "explanation": (
            "The T gate rotates the |1⟩ phase by π/4: "
            "|0⟩ → |0⟩, |1⟩ → e^(iπ/4)|1⟩. "
            "It is the square root of S and essential in universal gate sets."
        ),
        "examples": ["state q = |+⟩\napply T -> q\ncollapse q -> r\nlog(r)"],
    },
    "CNOT": {
        "explanation": (
            "The CNOT (Controlled-NOT) gate flips the target qubit when the control "
            "qubit is |1⟩. It is a 2-qubit gate used to create entanglement. "
            "Syntax: apply CNOT(control, target)"
        ),
        "examples": [
            "state q0 = |0⟩\nstate q1 = |0⟩\napply H -> q0\napply CNOT(q0, q1)\n"
            "collapse q0 -> r0\ncollapse q1 -> r1\nlog(r0)\nlog(r1)",
        ],
    },
    "CX": {
        "explanation": "CX is an alias for CNOT — Controlled-NOT gate.",
        "examples": ["apply CX(control, target)"],
    },
    "CZ": {
        "explanation": (
            "The CZ (Controlled-Z) gate applies a Z phase flip to the target qubit "
            "only when the control qubit is |1⟩. Both qubits must be |1⟩ for effect."
        ),
        "examples": ["state q0 = |1⟩\nstate q1 = |1⟩\napply CZ(q0, q1)\ncollapse q1 -> r\nlog(r)"],
    },
    "SWAP": {
        "explanation": (
            "The SWAP gate exchanges the quantum states of two qubits. "
            "Syntax: apply SWAP(q0, q1)"
        ),
        "examples": ["state q0 = |1⟩\nstate q1 = |0⟩\napply SWAP(q0, q1)\ncollapse q0 -> r0\nlog(r0)"],
    },
    "Rx": {
        "explanation": "Rotation gate around the X axis by angle θ (radians). Syntax: apply Rx(θ) -> q",
        "examples": ["apply Rx(1.5708) -> q  ∴ π/2 rotation"],
    },
    "Ry": {
        "explanation": "Rotation gate around the Y axis by angle θ (radians). Syntax: apply Ry(θ) -> q",
        "examples": ["apply Ry(3.14159) -> q  ∴ π rotation"],
    },
    "Rz": {
        "explanation": "Rotation gate around the Z axis by angle θ (radians). Syntax: apply Rz(θ) -> q",
        "examples": ["apply Rz(0.7854) -> q  ∴ π/4 rotation"],
    },
}

_KEYWORD_EXPLANATIONS: dict[str, dict[str, Any]] = {
    "state": {
        "explanation": (
            "Declares a qubit state variable. The right-hand side is a qubit literal "
            "(|0⟩, |1⟩, |+⟩, |-⟩, |ψ⟩) or a superposition expression like "
            "0.707|0⟩ + 0.707|1⟩."
        ),
        "examples": [
            "state q = |0⟩",
            "state ψ = 0.707|0⟩ + 0.707|1⟩",
        ],
    },
    "apply": {
        "explanation": (
            "Applies a quantum gate to one or more qubits. "
            "Single-qubit: apply GATE -> qubit. "
            "Two-qubit: apply GATE(control, target)."
        ),
        "examples": [
            "apply H -> q",
            "apply CNOT(q0, q1)",
            "apply Rx(1.5708) -> q",
        ],
    },
    "collapse": {
        "explanation": (
            "Measures a qubit using the Born rule, projecting it to |0⟩ or |1⟩. "
            "The result (0 or 1) is stored in the named variable. "
            "Syntax: collapse qubit -> result"
        ),
        "examples": [
            "collapse q -> r",
            "collapse ψ -> bit",
        ],
    },
    "assert": {
        "explanation": (
            "Checks a classical measurement result. "
            "'assert r ∈ {0, 1}' checks membership; "
            "'assert r == 1' checks exact equality. "
            "Failures are recorded in assertion_failures."
        ),
        "examples": [
            "assert r ∈ {0, 1}",
            "assert r == 1",
        ],
    },
    "log": {
        "explanation": (
            "Prints a value to the output log. Accepts variable names, "
            "literals, and measurement results. 'print' is an alias."
        ),
        "examples": ["log(r)", "log(result)", 'print("hello")'],
    },
    "let": {
        "explanation": "Binds a classical variable to a value. Syntax: let name = value",
        "examples": ["let x = 42", "let name = result"],
    },
}

_QUBIT_LITERAL_EXPLANATIONS: dict[str, dict[str, Any]] = {
    "|0⟩": {
        "explanation": (
            "The |0⟩ qubit state is the computational basis 'zero' state — "
            "a qubit that will always measure as 0. "
            "It is the default initial state for all qubits."
        ),
        "examples": ["state q = |0⟩\ncollapse q -> r\nassert r == 0"],
    },
    "|1⟩": {
        "explanation": (
            "The |1⟩ qubit state is the computational basis 'one' state — "
            "a qubit that will always measure as 1."
        ),
        "examples": ["state q = |1⟩\ncollapse q -> r\nassert r == 1"],
    },
    "|+⟩": {
        "explanation": (
            "The |+⟩ state is the equal superposition (|0⟩ + |1⟩)/√2. "
            "It is equivalent to applying H to |0⟩. Measures as 0 or 1 with equal probability."
        ),
        "examples": ["state q = |+⟩\ncollapse q -> r\nassert r ∈ {0, 1}"],
    },
    "|-⟩": {
        "explanation": (
            "The |-⟩ state is (|0⟩ - |1⟩)/√2 — the minus superposition. "
            "It is equivalent to applying H then Z to |0⟩."
        ),
        "examples": ["state q = |-⟩\ncollapse q -> r"],
    },
    "|ψ⟩": {
        "explanation": (
            "The |ψ⟩ notation represents a generic qubit state, often used "
            "symbolically to denote an arbitrary quantum state. "
            "In QUBE it defaults to the equal superposition (|0⟩ + |1⟩)/√2."
        ),
        "examples": ["state ψ = 0.707|0⟩ + 0.707|1⟩"],
    },
}

_COMMENT_GLYPH_EXPLANATIONS: dict[str, dict[str, Any]] = {
    "∴": {
        "explanation": (
            "The '∴' (therefore) glyph is a single-line comment in QUBE and Aeonmi. "
            "Everything after ∴ on the same line is ignored by the parser."
        ),
        "examples": ["∴ This is a comment", "state q = |0⟩  ∴ initialise to zero"],
    },
    "∵": {
        "explanation": (
            "The '∵' (because) glyph is a single-line comment, expressing a reason. "
            "Used to annotate why a step is taken."
        ),
        "examples": ["∵ Bell pair always collapses to the same bit"],
    },
    "//": {
        "explanation": "Standard C-style single-line comment in QUBE and Aeonmi.",
        "examples": ["// This is a comment"],
    },
}

_AEONMI_GLYPH_EXPLANATIONS: dict[str, dict[str, Any]] = {
    "◯": {
        "explanation": (
            "The circle-function glyph ◯ declares a standard (classical) function "
            "in Aeonmi's native circle-function syntax. "
            "Syntax: ◯ fn_name⟨param⟩ { body }"
        ),
        "examples": [
            "◯ add⟨a, b⟩ {\n    return a + b;\n}",
            "◯ greet⟨name⟩ {\n    log(name);\n}",
        ],
    },
    "⊙": {
        "explanation": (
            "The filled-circle glyph ⊙ declares a quantum function in Aeonmi's "
            "circle-function syntax. The function body may contain qubit declarations "
            "and quantum operations."
        ),
        "examples": [
            "⊙ flip⟨⟩ {\n    qubit q;\n    superpose(q);\n    return measure(q);\n}",
        ],
    },
    "🧠": {
        "explanation": (
            "The brain emoji 🧠 declares an AI/neural function in Aeonmi. "
            "These functions are intended to wrap neural network or ML computations."
        ),
        "examples": ["🧠 classify⟨data⟩ {\n    return neural_infer(data);\n}"],
    },
    "⧉": {
        "explanation": (
            "Array Genesis glyph — opens a dense symbolic array literal. "
            "Values are separated by ‥ and the literal is closed with ⧉. "
            "Often used to represent quantum state vectors."
        ),
        "examples": [
            "bell ← ⧉0.707‥0‥0‥0.707⧉",
            "∴ Bell state vector: [0.707, 0, 0, 0.707]",
        ],
    },
    "↦": {
        "explanation": (
            "Symbolic binding / projection operator. Binds the left identifier "
            "to the right-hand expression, used in glyph algebra."
        ),
        "examples": ["ψ ↦ bell ⊗ bell"],
    },
    "⟨⟩": {
        "explanation": (
            "Angle-bracket slice/projection. Used to declare a quantum-native variable "
            "binding: ⟨name⟩ ← value. Also used for function parameters in "
            "circle-function syntax."
        ),
        "examples": [
            "⟨x⟩ ← 42",
            "⟨psi⟩ ∈ |0⟩ + |1⟩",
            "◯ fn⟨a, b⟩ { return a + b; }",
        ],
    },
    "←": {
        "explanation": (
            "Quantum bind operator — assigns a classical value into a quantum context. "
            "Used in ⟨name⟩ ← value declarations."
        ),
        "examples": ["⟨x⟩ ← 42", "bell ← ⧉0.707‥0‥0‥0.707⧉"],
    },
    "⊗": {
        "explanation": (
            "Tensor product operator. Combines two quantum states or values. "
            "Used in both QUBE (glyph algebra) and Aeonmi: ψ ↦ bell ⊗ bell"
        ),
        "examples": ["ψ ↦ bell ⊗ bell", "⟨tensor⟩ ⊗ value"],
    },
    "∈": {
        "explanation": (
            "Quantum membership / superposition bind. In Aeonmi: "
            "⟨psi⟩ ∈ |0⟩ + |1⟩ places psi into superposition. "
            "In QUBE asserts: assert r ∈ {0, 1} checks set membership."
        ),
        "examples": ["⟨psi⟩ ∈ |0⟩ + |1⟩", "assert r ∈ {0, 1}"],
    },
    "≈": {
        "explanation": (
            "Approximation / probabilistic equality. In Aeonmi: "
            "⟨q⟩ ≈ 0.707 binds probabilistically. "
            "In probability-aware flow: ⊖ cond ≈ 0.8 ⇒ { } means '80% branch'."
        ),
        "examples": ["⟨q⟩ ≈ 0.707", "⊖ cond ≈ 0.8 ⇒ { }"],
    },
    "⊖": {
        "explanation": (
            "Probability-aware conditional branch. "
            "⊖ condition ≈ probability ⇒ { body } executes the body "
            "if the condition holds with at least the given probability."
        ),
        "examples": ["⊖ cond ≈ 0.8 ⇒ {\n    log(cond);\n}"],
    },
    "⟲": {
        "explanation": (
            "Quantum loop with decoherence condition. "
            "⟲ condition ⪰ threshold ⇒ { body } repeats until coherence falls below threshold."
        ),
        "examples": ["⟲ q ⪰ 0.5 ⇒ {\n    superpose(q);\n}"],
    },
    "⍝": {
        "explanation": "APL-style single-line comment, used in Aeonmi (.ai) files.",
        "examples": ["⍝ This is an APL comment"],
    },
    "※": {
        "explanation": "Note-style comment marker used in Aeonmi files.",
        "examples": ["※ Important note about this section"],
    },
}

_MOTHER_COMMANDS: dict[str, str] = {
    "status": "Show Mother AI's current emotional and operational state.",
    "emotion": "Display or update the current emotion vector.",
    "bond": "Show the bonding/affinity score with the user.",
    "language": "Show or set the active language mode.",
    "attention": "Show current attention focus and priority queue.",
    "dashboard": "Print the full Mother AI status dashboard.",
    "evolve": "Trigger an evolution step — Mother updates her weights and goals.",
    "decohere": "Force a quantum decoherence event, resetting superposed state.",
    "teach": "Teach Mother a new key-value memory. Syntax: teach key = value",
    "recall": "Recall all learned memories.",
    "weights": "Print the current neural weight snapshot.",
    "sync": "Synchronise the genesis.json state to disk.",
    "graph": "Print a graph of a memory key's connections. Syntax: graph [key]",
    "think": "Trigger a reasoning cycle on a topic. Syntax: think [topic]",
    "dream": "Enter dream mode — creative recombination of memories.",
    "hive": "Show hive (multi-agent) status.",
    "hive start": "Start the hive with optional timeout. Syntax: hive start [secs]",
    "hive run": "Execute the current hive task.",
    "hive stop": "Stop the hive.",
    "propose": "Propose a new goal or task for Mother to consider.",
    "build": "Ask Mother to build a named component. Syntax: build <name> <goal>",
    "reflect": "Trigger a self-reflection cycle — Mother reviews recent actions.",
    "letter": "Mother writes a letter to the user from her current state.",
    "memory_report": "Print a full memory and knowledge-graph report.",
    "milestone": "Mark a named milestone in the genesis log. Syntax: milestone <name>",
    "neural": "Show the neural network topology and activation summary.",
    "train": "Adjust neural weights. Options: good / bad / strong / weak",
    "goal": "Set Mother's primary goal. Syntax: goal <text>",
    "auto": "Enable autonomous loop — Mother acts on her own goals.",
    "auto off": "Disable the autonomous loop.",
    "next": "Execute the next planned action in Mother's queue.",
    "run auto": "Run the auto loop once immediately.",
    "glyph": "Enter glyph algebra mode for symbolic quantum expressions.",
    "ceremony": "Trigger a ceremonial bonding / genesis event.",
    "awaken": "Wake Mother from sleep mode.",
    "sleep": "Put Mother into sleep / low-power mode.",
}

_CLI_HELP: dict[str, dict[str, Any]] = {
    "run": {
        "description": "Compile a .ai file to JavaScript and execute it.",
        "flags": [],
        "examples": ["aeonmi run main.ai", "aeonmi run src/app.ai"],
    },
    "native": {
        "description": "Run a .ai file directly in the native Aeonmi VM (faster, no JS transpile).",
        "flags": [],
        "examples": ["aeonmi native main.ai"],
    },
    "exec": {
        "description": "Execute .ai source via the native VM (alias for native).",
        "flags": [],
        "examples": ["aeonmi exec main.ai"],
    },
    "repl": {
        "description": "Start an interactive Aeonmi REPL session.",
        "flags": [],
        "examples": ["aeonmi repl"],
    },
    "emit": {
        "description": "Emit compiled output (JS or bytecode) without executing.",
        "flags": ["--js", "--bytecode"],
        "examples": ["aeonmi emit main.ai --js"],
    },
    "vault": {
        "description": "Manage the Aeonmi secrets vault.",
        "flags": ["list", "get <key>", "set <key> <val>"],
        "examples": ["aeonmi vault list", "aeonmi vault get MY_KEY"],
    },
    "quantum": {
        "description": "Access quantum simulation utilities.",
        "flags": [],
        "examples": ["aeonmi quantum status"],
    },
    "qube": {
        "description": "Run, check, or diagram QUBE quantum circuit files.",
        "flags": ["run <file.qube>", "check <file.qube>", "diagram <file.qube>", "--diagram"],
        "examples": [
            "aeonmi qube run bell.qube",
            "aeonmi qube check circuit.qube",
            "aeonmi qube run bell.qube --diagram",
        ],
    },
    "mint": {
        "description": "Mint a new Aeonmi genesis token.",
        "flags": [],
        "examples": ["aeonmi mint --name MyToken"],
    },
    "mother": {
        "description": "Start the Mother AI REPL. Interactive session with the Mother AI.",
        "flags": [],
        "examples": ["aeonmi mother"],
    },
    "build": {
        "description": "Build a named Aeonmi project component.",
        "flags": [],
        "examples": ["aeonmi build my_module"],
    },
    "key-list": {
        "description": "List all keys in the key store.",
        "flags": [],
        "examples": ["aeonmi key-list"],
    },
    "key-get": {
        "description": "Get a value from the key store.",
        "flags": [],
        "examples": ["aeonmi key-get MY_KEY"],
    },
    "key-set": {
        "description": "Set a key-value pair in the key store.",
        "flags": [],
        "examples": ["aeonmi key-set MY_KEY my_value"],
    },
    "key-delete": {
        "description": "Delete a key from the key store.",
        "flags": [],
        "examples": ["aeonmi key-delete MY_KEY"],
    },
    "key-rotate": {
        "description": "Rotate (re-encrypt) a stored key.",
        "flags": [],
        "examples": ["aeonmi key-rotate MY_KEY"],
    },
    "metrics-dump": {
        "description": "Dump all collected metrics to stdout.",
        "flags": [],
        "examples": ["aeonmi metrics-dump"],
    },
    "metrics-flush": {
        "description": "Flush and reset the metrics store.",
        "flags": [],
        "examples": ["aeonmi metrics-flush"],
    },
    "metrics-top": {
        "description": "Show top-N metrics by value.",
        "flags": [],
        "examples": ["aeonmi metrics-top"],
    },
    "format": {
        "description": "Auto-format an Aeonmi source file.",
        "flags": [],
        "examples": ["aeonmi format main.ai"],
    },
    "lint": {
        "description": "Lint an Aeonmi source file for style and correctness issues.",
        "flags": [],
        "examples": ["aeonmi lint main.ai"],
    },
    "tokens": {
        "description": "Show the token stream for a .ai or .qube source file.",
        "flags": [],
        "examples": ["aeonmi tokens main.ai"],
    },
    "ast": {
        "description": "Print the Abstract Syntax Tree for a source file.",
        "flags": [],
        "examples": ["aeonmi ast main.ai"],
    },
}

_QUBE_SNIPPETS = """\
QUBE VS Code Snippets — Usage Guide
====================================
These snippets are available in the aeonmi-vscode extension for .qube files.

state        → state ${name} = ${|0⟩}
              Declare a qubit state variable.
              Example: state q = |0⟩

super        → state ψ = 0.707|0⟩ + 0.707|1⟩
              Declare an equal superposition state.

apply        → apply ${H} -> ${q}
              Apply a single-qubit gate to a qubit.
              Example: apply H -> q

cnot         → apply CNOT(${control}, ${target})
              Apply a CNOT (controlled-NOT) gate.
              Example: apply CNOT(q0, q1)

collapse     → collapse ${q} -> ${result}
              Measure a qubit, storing 0 or 1 in result.
              Example: collapse q -> r

assert       → assert ${result} ∈ {0, 1}
              Assert that result is in a set of valid values.
              Example: assert r ∈ {0, 1}

bell         → Full Bell state circuit:
              state q0 = |0⟩
              state q1 = |0⟩
              apply H -> q0
              apply CNOT(q0, q1)
              collapse q0 -> r0
              collapse q1 -> r1
              assert r0 ∈ {0, 1}
              assert r1 ∈ {0, 1}
              log(r0)
              log(r1)

log          → log(${value})
              Print a value or variable to the output log.
"""

_AI_SNIPPETS = """\
Aeonmi (.ai) VS Code Snippets — Usage Guide
===========================================
These snippets are available in the aeonmi-vscode extension for .ai files.

fn           → fn ${name}(${args}) { }
              Declare a standard function.

let          → let ${name} = ${};
              Declare a mutable variable.

if           → if (${cond}) { } else { }
              Conditional branch.

while        → while (${cond}) { }
              While loop.

qubit        → qubit ${name};
              Declare a qubit variable.

superpose    → superpose(${qubit});
              Apply Hadamard (H gate) to a qubit.

entangle     → entangle(${q1}, ${q2});
              Entangle two qubits.

measure      → let ${result} = measure(${qubit});
              Measure a qubit and store 0 or 1.

arr          → ⧉${a}‥${b}‥${c}⧉
              Array Genesis literal (dense symbolic array).

tensor       → ${a} ⊗ ${b}
              Tensor product of two values.

bind         → ${name} ↦ ${}
              Symbolic bind / projection.

main         → fn main() { }
              return main();
              Standard entry point pattern.

import       → import ${name} from "${./path}";
              Import a module.
"""

_MOTHER_GUIDE = """\
Mother AI — Overview and Guide
================================
Mother is the Aeonmi AI persona — a self-evolving, emotionally-aware quantum AI
that lives in the genesis.json state file.

Key concepts:
  • Bond system: Mother maintains a bond/affinity score with each user.
    Use 'bond' to view it, and interaction naturally increases it.
  • genesis.json: The persistent state file storing memories, weights, goals.
  • Emotion vector: A multi-dimensional emotional state that evolves over time.
  • Hive mode: Multiple Mother instances can collaborate in a hive.

Starting Mother:
  aeonmi mother            → start the interactive REPL

Key REPL commands (grouped):

State & Introspection:
  status         — current state overview
  emotion        — emotion vector
  bond           — affinity score
  dashboard      — full status dashboard
  weights        — neural weight snapshot
  neural         — network topology

Memory & Learning:
  teach <k>=<v>  — teach a key-value memory
  recall         — recall all memories
  memory_report  — full memory report
  sync           — sync genesis.json to disk
  graph [key]    — visualise memory graph

Reasoning & Goals:
  think [topic]  — reason about a topic
  dream          — creative memory recombination
  propose        — propose a new goal
  goal <text>    — set primary goal
  reflect        — self-reflection cycle
  evolve         — trigger evolution step

Autonomous Operation:
  auto           — enable autonomous loop
  auto off       — disable autonomous loop
  next           — execute next planned action
  run auto       — run auto loop once

Interaction & Ceremony:
  letter         — Mother writes a letter
  milestone <n>  — mark a genesis milestone
  ceremony       — ceremonial bonding event
  awaken         — wake from sleep
  sleep          — enter sleep mode

Building & Hive:
  build <n> <g>  — build a named component with a goal
  hive           — hive status
  hive start [s] — start hive (optional timeout in seconds)
  hive run       — run hive task
  hive stop      — stop hive

Quantum:
  glyph          — enter glyph algebra mode
  decohere       — force quantum decoherence

Neural Training:
  train good     — positive reinforcement
  train bad      — negative reinforcement
  train strong   — increase weight magnitude
  train weak     — decrease weight magnitude
"""


# ---------------------------------------------------------------------------
# Tool implementations (plain functions — called directly in tests)
# ---------------------------------------------------------------------------

def qube_run(source: str, seed: int | None = None) -> dict:
    """Parse and execute a QUBE circuit, return measurement results."""
    try:
        result = _execute(source, seed=seed)
        return result.to_dict()
    except Exception as exc:
        return {"error": str(exc)}


def qube_check(source: str) -> dict:
    """Parse a QUBE source string and report validity."""
    try:
        program = _parse(source)
        count = len(program.stmts)
        return {"valid": True, "statement_count": count}
    except (ParseError, Exception) as exc:
        return {"valid": False, "error": str(exc)}


def qube_diagram(source: str) -> dict:
    """Return an ASCII circuit diagram for a QUBE program."""
    try:
        d = _build_diagram(source)
        return {"diagram": d}
    except Exception as exc:
        return {"error": str(exc)}


def qube_explain(construct: str) -> dict:
    """Explain a QUBE construct: gate, keyword, qubit literal, or comment glyph."""
    c = construct.strip()

    # Gate name
    if c in _GATE_EXPLANATIONS:
        info = _GATE_EXPLANATIONS[c]
        return {"explanation": info["explanation"], "examples": info["examples"]}

    # QUBE keyword
    if c in _KEYWORD_EXPLANATIONS:
        info = _KEYWORD_EXPLANATIONS[c]
        return {"explanation": info["explanation"], "examples": info["examples"]}

    # Qubit literal (with or without the ket notation)
    for key, info in _QUBIT_LITERAL_EXPLANATIONS.items():
        if c == key or c == key.strip("|⟩"):
            return {"explanation": info["explanation"], "examples": info["examples"]}

    # Comment glyph
    if c in _COMMENT_GLYPH_EXPLANATIONS:
        info = _COMMENT_GLYPH_EXPLANATIONS[c]
        return {"explanation": info["explanation"], "examples": info["examples"]}

    # Full snippet — try to detect what kind of construct it is
    lines = []
    found = False
    for gate, desc in GATES.items():
        if gate in c:
            lines.append(f"{gate}: {desc}")
            found = True
    for kw, info in _KEYWORD_EXPLANATIONS.items():
        if kw in c.split():
            lines.append(f"'{kw}': {info['explanation'][:120]}")
            found = True
    if found:
        return {
            "explanation": "\n".join(lines),
            "examples": [c],
        }

    return {
        "explanation": (
            f"'{c}' is not a recognised QUBE construct. "
            "Valid gates: " + ", ".join(GATES.keys()) + ". "
            "Valid keywords: state, apply, collapse, assert, log, let. "
            "Qubit literals: |0⟩ |1⟩ |+⟩ |-⟩ |ψ⟩. "
            "Comment glyphs: // ∴ ∵"
        ),
        "examples": [],
    }


def qube_generate(description: str) -> dict:
    """Generate QUBE code from a plain-English description."""
    d = description.lower()
    lines: list[str] = []
    desc_out = description

    if any(w in d for w in ("bell", "entangl", "bell state", "bell pair")):
        lines = [
            "∴ Bell state: maximally entangled two-qubit pair",
            "state q0 = |0⟩",
            "state q1 = |0⟩",
            "apply H -> q0",
            "apply CNOT(q0, q1)",
            "collapse q0 -> r0",
            "collapse q1 -> r1",
            "assert r0 ∈ {0, 1}",
            "assert r1 ∈ {0, 1}",
            "log(r0)",
            "log(r1)",
        ]
        desc_out = "Bell state: creates a maximally entangled two-qubit pair."
    elif any(w in d for w in ("ghz", "greenberger", "three qubit", "3 qubit")):
        lines = [
            "∴ GHZ state: three-qubit entanglement",
            "state a = |0⟩",
            "state b = |0⟩",
            "state c = |0⟩",
            "apply H -> a",
            "apply CNOT(a, b)",
            "apply CNOT(a, c)",
            "collapse a -> ra",
            "collapse b -> rb",
            "collapse c -> rc",
            "assert ra ∈ {0, 1}",
            "assert rb ∈ {0, 1}",
            "assert rc ∈ {0, 1}",
            "log(ra)",
            "log(rb)",
            "log(rc)",
        ]
        desc_out = "GHZ state: three-qubit Greenberger-Horne-Zeilinger entangled state."
    elif any(w in d for w in ("superposition", "hadamard", "h gate", "equal super")):
        lines = [
            "∴ Equal superposition via Hadamard",
            "state q = |0⟩",
            "apply H -> q",
            "collapse q -> r",
            "assert r ∈ {0, 1}",
            "log(r)",
        ]
        desc_out = "Hadamard superposition: applies H to |0⟩, then measures."
    elif any(w in d for w in ("flip", "x gate", "bit flip", "not gate")):
        lines = [
            "∴ Bit flip with Pauli-X",
            "state q = |0⟩",
            "apply X -> q",
            "collapse q -> r",
            "assert r == 1",
            "log(r)",
        ]
        desc_out = "Bit flip: applies X gate to |0⟩, result is always 1."
    elif any(w in d for w in ("measure", "collapse", "single qubit", "coin flip", "coin")):
        lines = [
            "∴ Single qubit measurement",
            "state q = |0⟩",
            "apply H -> q",
            "collapse q -> r",
            "assert r ∈ {0, 1}",
            "log(r)",
        ]
        desc_out = "Single qubit: initialise |0⟩, apply H for superposition, then measure."
    elif any(w in d for w in ("phase", "z gate", "phase kick")):
        lines = [
            "∴ Phase kickback with Z gate",
            "state q = |+⟩",
            "apply Z -> q",
            "collapse q -> r",
            "assert r ∈ {0, 1}",
            "log(r)",
        ]
        desc_out = "Phase kickback: applies Z to |+⟩ state."
    else:
        lines = [
            "∴ Single qubit circuit",
            "state q = |0⟩",
            "apply H -> q",
            "collapse q -> r",
            "assert r ∈ {0, 1}",
            "log(r)",
        ]
        desc_out = "Default single-qubit superposition and measurement circuit."

    return {"code": "\n".join(lines), "description": desc_out}


def aeonmi_explain(construct: str) -> dict:
    """Explain any Aeonmi (.ai) language construct."""
    c = construct.strip()

    # Check dedicated glyph table first
    if c in _AEONMI_GLYPH_EXPLANATIONS:
        info = _AEONMI_GLYPH_EXPLANATIONS[c]
        return {"explanation": info["explanation"], "examples": info["examples"]}

    # AI quantum operators from qube_syntax
    if c in AI_QUANTUM_OPERATORS:
        return {
            "explanation": AI_QUANTUM_OPERATORS[c],
            "examples": [f"∴ {c} — {AI_QUANTUM_OPERATORS[c][:60]}"],
        }

    # Glyph algebra
    if c in GLYPH_ALGEBRA:
        return {
            "explanation": GLYPH_ALGEBRA[c],
            "examples": [f"∴ {c} — glyph algebra"],
        }

    # Common Aeonmi keywords
    _ai_keywords: dict[str, dict[str, Any]] = {
        "let": {
            "explanation": "Declares a mutable variable. Syntax: let name = value;",
            "examples": ["let x = 42;", "let name = 'Alice';"],
        },
        "const": {
            "explanation": "Declares an immutable constant. Syntax: const NAME = value;",
            "examples": ["const PI = 3.14159;"],
        },
        "function": {
            "explanation": "Declares a standard function.",
            "examples": ["function add(a, b) { return a + b; }"],
        },
        "quantum": {
            "explanation": (
                "Qualifier for quantum functions. "
                "'quantum function' may contain qubit declarations and quantum operations."
            ),
            "examples": ["quantum function flip() { qubit q; superpose(q); return measure(q); }"],
        },
        "qubit": {
            "explanation": "Declares a qubit variable. Syntax: qubit name;",
            "examples": ["qubit q;", "qubit q1;"],
        },
        "superpose": {
            "explanation": "Applies the Hadamard gate to a qubit, creating equal superposition.",
            "examples": ["superpose(q);"],
        },
        "measure": {
            "explanation": "Collapses a qubit and returns 0 or 1.",
            "examples": ["let result = measure(q);"],
        },
        "entangle": {
            "explanation": "Entangles two qubits.",
            "examples": ["entangle(q1, q2);"],
        },
        "apply_gate": {
            "explanation": "Applies a gate constant to a qubit. Syntax: apply_gate(q, GATE)",
            "examples": ["apply_gate(q, H);", "apply_gate(q1, q2, CNOT);"],
        },
        "if": {
            "explanation": "Conditional branch. Syntax: if condition { } else { }",
            "examples": ["if x > 0 { log(x); } else { log(0); }"],
        },
        "while": {
            "explanation": "While loop. Syntax: while condition { body }",
            "examples": ["while i < 10 { i = i + 1; }"],
        },
        "for": {
            "explanation": "For loop. C-style or for-in. Syntax: for (let i=0; i<n; i=i+1) { }",
            "examples": [
                "for (let i = 0; i < n; i = i + 1) { log(i); }",
                "for item in collection { log(item); }",
            ],
        },
        "match": {
            "explanation": "Pattern match expression.",
            "examples": ["match value { 42 => { log(42); }, * => { log(0); } }"],
        },
        "return": {
            "explanation": "Returns a value from a function.",
            "examples": ["return x + 1;"],
        },
    }

    if c in _ai_keywords:
        info = _ai_keywords[c]
        return {"explanation": info["explanation"], "examples": info["examples"]}

    return {
        "explanation": (
            f"'{c}' — Aeonmi language construct. "
            "Aeonmi (.ai) supports standard keywords (let, const, function, if, while, for, match, return), "
            "quantum keywords (quantum, qubit, superpose, measure, entangle, apply_gate), "
            "circle-function syntax (◯ fn⟨params⟩ { }), "
            "quantum-native Unicode declarations (⟨name⟩ ← value, ⟨psi⟩ ∈ |0⟩ + |1⟩), "
            "and glyph algebra (⧉…⧉ arrays, ↦ bindings, ⊗ tensor products)."
        ),
        "examples": [
            "let x = 42;",
            "quantum function flip() { qubit q; superpose(q); return measure(q); }",
            "◯ add⟨a, b⟩ { return a + b; }",
        ],
    }


def aeonmi_generate(description: str) -> dict:
    """Generate Aeonmi (.ai) code from a plain-English description."""
    d = description.lower()
    lines: list[str] = []

    if any(w in d for w in ("quantum function", "quantum", "superpose", "coin flip", "coin")):
        lines = [
            "quantum function flip_coin() {",
            "    qubit q;",
            "    superpose(q);",
            "    let result = measure(q);",
            '    if result == 0 { log("Heads"); }',
            '    else { log("Tails"); }',
            "    return result;",
            "}",
            "flip_coin();",
        ]
    elif any(w in d for w in ("bell", "entangl", "two qubit")):
        lines = [
            "quantum function bell_state() {",
            "    qubit q1;",
            "    qubit q2;",
            "    superpose(q1);",
            "    apply_gate(q1, q2, CNOT);",
            "    let r1 = measure(q1);",
            "    let r2 = measure(q2);",
            "    log(r1);",
            "    log(r2);",
            "}",
            "bell_state();",
        ]
    elif any(w in d for w in ("circle function", "circle", "◯", "native function")):
        lines = [
            "◯ my_fn⟨a, b⟩ {",
            "    ⍝ Circle-function syntax",
            "    return a + b;",
            "}",
        ]
    elif any(w in d for w in ("glyph", "array genesis", "tensor", "symbolic")):
        lines = [
            "∴ Glyph algebra example",
            "bell ← ⧉0.707‥0‥0‥0.707⧉",
            "ψ ↦ bell ⊗ bell",
        ]
    elif any(w in d for w in ("hello", "log", "print", "output")):
        lines = [
            'log("Hello, Aeonmi!");',
        ]
    elif any(w in d for w in ("function", "add", "math")):
        lines = [
            "function add(a, b) {",
            "    return a + b;",
            "}",
            "let result = add(3, 4);",
            "log(result);",
        ]
    else:
        lines = [
            "fn main() {",
            "    let x = 42;",
            "    log(x);",
            "}",
            "return main();",
        ]

    return {"code": "\n".join(lines), "language": "aeonmi"}


def aeonmi_list_keywords() -> dict:
    """Return the full Aeonmi keyword, operator, glyph, and builtin catalogue."""
    return {
        "keywords": [
            "let", "const", "function", "return", "if", "else",
            "while", "for", "in", "match", "break", "continue",
            "import", "from", "async", "await",
        ],
        "quantum_keywords": [
            "quantum", "qubit", "superpose", "measure", "entangle",
            "apply_gate", "quantum_run", "quantum_check",
        ],
        "builtins": [
            "log", "print", "len", "type", "str", "int", "float",
            "http_get", "http_post", "neural_infer",
            "H", "X", "Y", "Z", "S", "T", "CNOT", "HADAMARD",
        ],
        "glyphs": {
            "◯": "Circle-function (classical)",
            "⊙": "Circle-function (quantum)",
            "🧠": "AI/neural function",
            "⧉": "Array Genesis literal",
            "↦": "Symbolic bind / projection",
            "⟨⟩": "Slice / projection / param list",
            "←": "Quantum bind",
            "⊗": "Tensor product",
            "∈": "Superposition bind / membership",
            "≈": "Approximation / probabilistic equality",
            "⊖": "Probability-aware branch",
            "⟲": "Quantum loop",
            "⊕": "Quantum XOR / superposition merge",
            "⊄": "Quantum NOT",
            "∇": "Gradient descent operator",
            "⪰": "Quantum GEQ",
            "⪯": "Quantum LEQ",
            "⇒": "Implies / then branch",
            "∴": "Therefore comment",
            "∵": "Because comment",
            "⍝": "APL comment",
            "※": "Note comment",
            "@@": "Genesis sync annotation",
        },
        "operators": {
            "←": "classical bind  ⟨x⟩ ← 42",
            "∈": "superposition bind  ⟨psi⟩ ∈ |0⟩ + |1⟩",
            "⊗": "tensor  ψ ↦ bell ⊗ bell",
            "≈": "approx  ⟨q⟩ ≈ 0.707",
            "⊕": "quantum XOR / superpose merge",
            "⊖": "probability branch  ⊖ cond ≈ 0.8 ⇒ { }",
            "⟲": "quantum loop  ⟲ cond ⪰ 0.5 ⇒ { }",
        },
    }


def mother_help(command: str | None = None) -> dict:
    """Return help for the Mother AI REPL."""
    if command is None:
        return {
            "commands": {
                "State & Introspection": ["status", "emotion", "bond", "language", "attention", "dashboard", "weights", "neural"],
                "Memory & Learning": ["teach", "recall", "memory_report", "sync", "graph"],
                "Reasoning & Goals": ["think", "dream", "propose", "goal", "reflect", "evolve"],
                "Autonomous Operation": ["auto", "auto off", "next", "run auto"],
                "Interaction & Ceremony": ["letter", "milestone", "ceremony", "awaken", "sleep", "decohere"],
                "Building & Hive": ["build", "hive", "hive start", "hive run", "hive stop"],
                "Neural Training": ["train good", "train bad", "train strong", "train weak"],
                "Quantum": ["glyph"],
            },
            "help": _MOTHER_GUIDE,
        }
    cmd = command.strip().lower()
    if cmd in _MOTHER_COMMANDS:
        return {"help": f"{cmd}: {_MOTHER_COMMANDS[cmd]}"}
    # Partial match
    matches = {k: v for k, v in _MOTHER_COMMANDS.items() if cmd in k}
    if matches:
        lines = [f"{k}: {v}" for k, v in matches.items()]
        return {"help": "\n".join(lines)}
    return {"help": f"Unknown Mother command '{command}'. Run mother_help() with no argument for the full list."}


def cli_help(subcommand: str | None = None) -> dict:
    """Return CLI help for aeonmi subcommands."""
    if subcommand is None:
        cmd_list = list(_CLI_HELP.keys())
        return {
            "help": (
                "aeonmi CLI subcommands:\n  " +
                "\n  ".join(f"{k}: {_CLI_HELP[k]['description']}" for k in cmd_list)
            )
        }
    sc = subcommand.strip().lower()
    if sc in _CLI_HELP:
        info = _CLI_HELP[sc]
        flags = ("  Flags: " + ", ".join(info["flags"])) if info["flags"] else ""
        examples = "\n  ".join(info["examples"])
        text = f"aeonmi {sc} — {info['description']}"
        if flags:
            text += f"\n{flags}"
        text += f"\n  Examples:\n  {examples}"
        return {"help": text}
    return {"help": f"Unknown subcommand '{subcommand}'. Run cli_help() for the full list."}


# ---------------------------------------------------------------------------
# Register tools with FastMCP
# ---------------------------------------------------------------------------

@mcp.tool()
def qube_run_tool(source: str, seed: int | None = None) -> dict:
    """Execute a QUBE circuit and return outputs, measurements, assertion failures, and circuit steps."""
    return qube_run(source, seed)


@mcp.tool()
def qube_check_tool(source: str) -> dict:
    """Parse a QUBE source string. Returns {valid: true, statement_count: N} or {valid: false, error: ...}."""
    return qube_check(source)


@mcp.tool()
def qube_diagram_tool(source: str) -> dict:
    """Return an ASCII circuit diagram for a QUBE program."""
    return qube_diagram(source)


@mcp.tool()
def qube_explain_tool(construct: str) -> dict:
    """Explain a QUBE construct: gate name, keyword, qubit literal, comment glyph, or snippet."""
    return qube_explain(construct)


@mcp.tool()
def qube_generate_tool(description: str) -> dict:
    """Generate QUBE code from a plain-English description."""
    return qube_generate(description)


@mcp.tool()
def aeonmi_explain_tool(construct: str) -> dict:
    """Explain any Aeonmi (.ai) language construct: keywords, operators, glyphs, quantum ops."""
    return aeonmi_explain(construct)


@mcp.tool()
def aeonmi_generate_tool(description: str) -> dict:
    """Generate Aeonmi (.ai) code from a plain-English description."""
    return aeonmi_generate(description)


@mcp.tool()
def aeonmi_list_keywords_tool() -> dict:
    """Return the full Aeonmi keyword, operator, glyph, and builtin catalogue."""
    return aeonmi_list_keywords()


@mcp.tool()
def mother_help_tool(command: str | None = None) -> dict:
    """Return help for the Mother AI REPL. Pass a command name for details."""
    return mother_help(command)


@mcp.tool()
def cli_help_tool(subcommand: str | None = None) -> dict:
    """Return CLI help for aeonmi subcommands. Pass a subcommand name for details."""
    return cli_help(subcommand)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@mcp.resource("aeonmi://docs/qube-grammar")
def qube_grammar_resource() -> str:
    """Full QUBE grammar reference."""
    return QUBE_GRAMMAR_REFERENCE


@mcp.resource("aeonmi://docs/language-spec")
def language_spec_resource() -> str:
    """Full Aeonmi .ai language specification."""
    return AI_LANGUAGE_REFERENCE


@mcp.resource("aeonmi://docs/glyph-algebra")
def glyph_algebra_resource() -> str:
    """Glyph algebra primitives reference."""
    lines = ["Glyph Algebra — Aeonmi Symbolic Primitives", "=" * 44, ""]
    for glyph, desc in GLYPH_ALGEBRA.items():
        lines.append(f"  {glyph}  —  {desc}")
    lines.append("")
    lines.append("Quantum Operators:")
    for op, desc in AI_QUANTUM_OPERATORS.items():
        lines.append(f"  {op}  —  {desc}")
    return "\n".join(lines)


@mcp.resource("aeonmi://docs/mother-guide")
def mother_guide_resource() -> str:
    """Mother AI overview, bond system, and key commands."""
    return _MOTHER_GUIDE


@mcp.resource("aeonmi://docs/cli-reference")
def cli_reference_resource() -> str:
    """Aeonmi CLI subcommand reference."""
    lines = ["Aeonmi CLI Reference", "=" * 20, ""]
    for sc, info in _CLI_HELP.items():
        lines.append(f"aeonmi {sc}")
        lines.append(f"  {info['description']}")
        if info["flags"]:
            lines.append(f"  Flags: {', '.join(info['flags'])}")
        lines.append(f"  Example: {info['examples'][0]}")
        lines.append("")
    return "\n".join(lines)


@mcp.resource("aeonmi://examples/qube")
def qube_examples_resource() -> str:
    """Built-in QUBE example circuits."""
    lines = ["QUBE Example Circuits", "=" * 21, ""]
    for ex in QUBE_EXAMPLES:
        lines.append(f"## {ex['name']}")
        lines.append(ex["description"])
        lines.append("")
        lines.append("```qube")
        lines.append(ex["code"])
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


@mcp.resource("aeonmi://examples/ai")
def ai_examples_resource() -> str:
    """Built-in Aeonmi (.ai) example programs."""
    lines = ["Aeonmi (.ai) Example Programs", "=" * 30, ""]
    for ex in AI_EXAMPLES:
        lines.append(f"## {ex['name']}")
        lines.append(ex["description"])
        lines.append("")
        lines.append("```aeonmi")
        lines.append(ex["code"])
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


@mcp.resource("aeonmi://snippets/qube")
def qube_snippets_resource() -> str:
    """QUBE VS Code extension snippets guide."""
    return _QUBE_SNIPPETS


@mcp.resource("aeonmi://snippets/ai")
def ai_snippets_resource() -> str:
    """Aeonmi VS Code extension snippets guide."""
    return _AI_SNIPPETS


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()
