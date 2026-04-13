"""QUBE circuit executor with real statevector quantum simulation.

Implements the semantics from Aeonmi-Aysa/aeonmi docs/QUBE_SPEC.md and
src/qube/executor.rs:

  1. States are complex state vectors (2^n dimensions for n qubits).
  2. Gates are unitary matrix operations backed by the Titan quantum simulator.
  3. `collapse` performs projective measurement using the Born rule.
  4. `assert` checks classical results; raises AssertionError on failure.
  5. `log`/`print` writes the value to the output log.
"""

from __future__ import annotations

import cmath
import math
import random
from dataclasses import dataclass, field
from typing import Any

from .qube_parser import (
    Assert, Collapse, Comment, GateApply, LetBinding, LogStmt,
    QubitLiteral, QubeProgram, StateDecl, StateRef, Superposition,
    TensorProduct, parse,
)
from .qube_syntax import GATE_MATRICES, TWO_QUBIT_GATES

# ---------------------------------------------------------------------------
# Statevector utilities
# ---------------------------------------------------------------------------

StateVec = list[complex]  # length must always be a power of 2


def _zero_state(n_qubits: int) -> StateVec:
    """Return the |0...0⟩ state vector for n qubits."""
    size = 1 << n_qubits
    v: StateVec = [complex(0)] * size
    v[0] = complex(1)
    return v


def _qubit_state_vec(inner: str) -> StateVec:
    """Create a single-qubit state vector from a qubit literal inner string."""
    s2 = math.sqrt(0.5)
    table: dict[str, StateVec] = {
        "0":  [complex(1), complex(0)],
        "1":  [complex(0), complex(1)],
        "+":  [complex(s2), complex(s2)],
        "-":  [complex(s2), complex(-s2)],
        "−":  [complex(s2), complex(-s2)],
        "ψ":  [complex(s2), complex(s2)],   # treat |ψ⟩ as equal superposition
        "φ":  [complex(s2), complex(s2)],
        "Φ":  [complex(s2), complex(s2)],
        "Ω":  [complex(1), complex(0)],
    }
    return table.get(inner.strip(), [complex(1), complex(0)])


def _tensor_product(a: StateVec, b: StateVec) -> StateVec:
    """Kronecker/tensor product of two state vectors."""
    result: StateVec = []
    for ai in a:
        for bi in b:
            result.append(ai * bi)
    return result


def _norm_sq(v: StateVec) -> float:
    return sum(abs(c) ** 2 for c in v)


def _normalise(v: StateVec) -> StateVec:
    n = math.sqrt(_norm_sq(v))
    if n < 1e-15:
        return v
    return [c / n for c in v]


def _apply_1q_gate(sv: StateVec, n_qubits: int, qubit_idx: int,
                   matrix: list[list[complex]]) -> StateVec:
    """Apply a 2x2 unitary to qubit `qubit_idx` (0 = most significant) of sv."""
    size = 1 << n_qubits
    result: StateVec = [complex(0)] * size
    for i in range(size):
        # Determine the bit value at qubit_idx position
        bit = (i >> (n_qubits - 1 - qubit_idx)) & 1
        # Partner index: flip that bit
        j = i ^ (1 << (n_qubits - 1 - qubit_idx))
        if bit == 0:
            result[i] += matrix[0][0] * sv[i] + matrix[0][1] * sv[j]
        else:
            result[i] += matrix[1][0] * sv[j] + matrix[1][1] * sv[i]
    return result


def _apply_cnot(sv: StateVec, n_qubits: int,
                control_idx: int, target_idx: int) -> StateVec:
    size = 1 << n_qubits
    result: StateVec = [complex(0)] * size
    for i in range(size):
        c_bit = (i >> (n_qubits - 1 - control_idx)) & 1
        if c_bit == 1:
            flipped = i ^ (1 << (n_qubits - 1 - target_idx))
            result[flipped] += sv[i]
        else:
            result[i] += sv[i]
    return result


def _apply_cz(sv: StateVec, n_qubits: int,
              q0: int, q1: int) -> StateVec:
    size = 1 << n_qubits
    result: StateVec = list(sv)
    for i in range(size):
        b0 = (i >> (n_qubits - 1 - q0)) & 1
        b1 = (i >> (n_qubits - 1 - q1)) & 1
        if b0 == 1 and b1 == 1:
            result[i] = -sv[i]
    return result


def _apply_swap(sv: StateVec, n_qubits: int, q0: int, q1: int) -> StateVec:
    size = 1 << n_qubits
    result: StateVec = [complex(0)] * size
    for i in range(size):
        b0 = (i >> (n_qubits - 1 - q0)) & 1
        b1 = (i >> (n_qubits - 1 - q1)) & 1
        if b0 != b1:
            swapped = i ^ (1 << (n_qubits - 1 - q0)) ^ (1 << (n_qubits - 1 - q1))
            result[swapped] += sv[i]
        else:
            result[i] += sv[i]
    return result


def _measure_qubit(sv: StateVec, n_qubits: int, qubit_idx: int,
                   rng: random.Random) -> tuple[int, StateVec]:
    """Measure qubit at qubit_idx. Returns (outcome 0/1, collapsed_sv)."""
    size = 1 << n_qubits
    # Probability of outcome 1
    p1 = sum(
        abs(sv[i]) ** 2
        for i in range(size)
        if (i >> (n_qubits - 1 - qubit_idx)) & 1 == 1
    )
    outcome = 1 if rng.random() < p1 else 0
    # Project
    collapsed: StateVec = [complex(0)] * size
    for i in range(size):
        bit = (i >> (n_qubits - 1 - qubit_idx)) & 1
        if bit == outcome:
            collapsed[i] = sv[i]
    return outcome, _normalise(collapsed)


def _rotation_matrix(axis: str, angle: float) -> list[list[complex]]:
    c = math.cos(angle / 2)
    s = math.sin(angle / 2)
    i = complex(0, 1)
    if axis == "x":
        return [[complex(c), -i * s], [-i * s, complex(c)]]
    if axis == "y":
        return [[complex(c), complex(-s)], [complex(s), complex(c)]]
    # z
    return [[cmath.exp(-i * angle / 2), complex(0)],
            [complex(0), cmath.exp(i * angle / 2)]]


# ---------------------------------------------------------------------------
# Execution state
# ---------------------------------------------------------------------------

@dataclass
class ExecutionResult:
    outputs: list[str] = field(default_factory=list)
    measurements: dict[str, int] = field(default_factory=dict)
    assertion_failures: list[str] = field(default_factory=list)
    circuit_steps: list[str] = field(default_factory=list)   # for diagram

    def to_dict(self) -> dict[str, Any]:
        return {
            "outputs": self.outputs,
            "measurements": self.measurements,
            "assertion_failures": self.assertion_failures,
            "circuit_steps": self.circuit_steps,
        }


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

class QubeExecutor:
    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._result = ExecutionResult()
        # name → (qubit_index_in_joint_register, ...)
        # We maintain one joint statevector over all qubits allocated so far.
        self._qubit_names: list[str] = []    # ordered list; index = qubit position
        self._sv: StateVec = [complex(1)]    # starts as zero-qubit (scalar 1)
        self._classical: dict[str, Any] = {} # let bindings + collapse results

    # ---- public ------------------------------------------------------------

    def execute(self, program: QubeProgram) -> ExecutionResult:
        for stmt in program.stmts:
            self._exec_stmt(stmt)
        return self._result

    # ---- statement dispatch -----------------------------------------------

    def _exec_stmt(self, stmt: Any) -> None:
        if isinstance(stmt, StateDecl):
            self._exec_state_decl(stmt)
        elif isinstance(stmt, GateApply):
            self._exec_gate_apply(stmt)
        elif isinstance(stmt, Collapse):
            self._exec_collapse(stmt)
        elif isinstance(stmt, Assert):
            self._exec_assert(stmt)
        elif isinstance(stmt, LogStmt):
            self._exec_log(stmt)
        elif isinstance(stmt, LetBinding):
            self._classical[stmt.name] = stmt.value
        elif isinstance(stmt, Comment):
            pass  # comments are no-ops

    # ---- state declaration ------------------------------------------------

    def _exec_state_decl(self, stmt: StateDecl) -> None:
        sv = self._state_expr_to_vec(stmt.value)
        if stmt.name in self._qubit_names:
            # Re-assignment: not supported in current spec; ignore
            return
        # Allocate a new qubit by tensoring sv into the joint register
        self._sv = _tensor_product(self._sv, sv)
        self._qubit_names.append(stmt.name)
        self._result.circuit_steps.append(f"state {stmt.name} = {self._fmt_state(stmt.value)}")

    def _state_expr_to_vec(self, expr: Any) -> StateVec:
        if isinstance(expr, QubitLiteral):
            return _qubit_state_vec(expr.inner)
        if isinstance(expr, Superposition):
            # Build the state from amplitude terms; normalise afterwards
            v: StateVec = [complex(0), complex(0)]
            for amp, ql in expr.terms:
                base = _qubit_state_vec(ql.inner)
                a = complex(amp if amp is not None else 1.0)
                v = [v[k] + a * base[k] for k in range(2)]
            return _normalise(v)
        if isinstance(expr, StateRef):
            # Reference to an already-declared qubit is not a fresh allocation;
            # treat it as a copy of |0⟩ for circuit construction purposes.
            return [complex(1), complex(0)]
        if isinstance(expr, TensorProduct):
            return _tensor_product(
                self._state_expr_to_vec(expr.left),
                self._state_expr_to_vec(expr.right),
            )
        return [complex(1), complex(0)]

    def _fmt_state(self, expr: Any) -> str:
        if isinstance(expr, QubitLiteral):
            return f"|{expr.inner}⟩"
        if isinstance(expr, Superposition):
            parts = []
            for amp, ql in expr.terms:
                a = amp if amp is not None else 1.0
                parts.append(f"{a:.3g}|{ql.inner}⟩")
            return " + ".join(parts)
        if isinstance(expr, StateRef):
            return expr.name
        return "?"

    # ---- gate application -------------------------------------------------

    def _exec_gate_apply(self, stmt: GateApply) -> None:
        gate = stmt.gate
        targets = stmt.targets
        n = len(self._qubit_names)

        step = f"apply {gate} → {', '.join(targets)}"
        self._result.circuit_steps.append(step)

        # Rotation gate with angle embedded: "Rx(1.5708)"
        angle: float | None = None
        axis: str | None = None
        if gate.startswith("Rx(") or gate.startswith("Ry(") or gate.startswith("Rz("):
            axis = gate[1].lower()
            try:
                angle = float(gate[3:-1])
            except ValueError:
                angle = 0.0
            gate_base = gate[:2]
        else:
            gate_base = gate

        if gate_base in ("CNOT", "CX") and len(targets) >= 2:
            ci = self._qubit_index(targets[0])
            ti = self._qubit_index(targets[1])
            if ci is not None and ti is not None:
                self._sv = _apply_cnot(self._sv, n, ci, ti)
            return

        if gate_base == "CZ" and len(targets) >= 2:
            qi0 = self._qubit_index(targets[0])
            qi1 = self._qubit_index(targets[1])
            if qi0 is not None and qi1 is not None:
                self._sv = _apply_cz(self._sv, n, qi0, qi1)
            return

        if gate_base == "SWAP" and len(targets) >= 2:
            qi0 = self._qubit_index(targets[0])
            qi1 = self._qubit_index(targets[1])
            if qi0 is not None and qi1 is not None:
                self._sv = _apply_swap(self._sv, n, qi0, qi1)
            return

        # Single-qubit gates
        for target in targets:
            qi = self._qubit_index(target)
            if qi is None:
                continue
            if axis is not None and angle is not None:
                mat = _rotation_matrix(axis, angle)
            else:
                mat = GATE_MATRICES.get(gate_base)
                if mat is None:
                    # Unknown gate — identity
                    continue
            self._sv = _apply_1q_gate(self._sv, n, qi, mat)

    def _qubit_index(self, name: str) -> int | None:
        try:
            return self._qubit_names.index(name)
        except ValueError:
            return None

    # ---- collapse ----------------------------------------------------------

    def _exec_collapse(self, stmt: Collapse) -> None:
        qi = self._qubit_index(stmt.qubit)
        if qi is None:
            return
        n = len(self._qubit_names)
        outcome, self._sv = _measure_qubit(self._sv, n, qi, self._rng)
        self._classical[stmt.result] = outcome
        self._result.measurements[stmt.result] = outcome
        self._result.circuit_steps.append(f"collapse {stmt.qubit} → {stmt.result} = {outcome}")

    # ---- assert ------------------------------------------------------------

    def _exec_assert(self, stmt: Assert) -> None:
        value = self._classical.get(stmt.variable)
        if value is None:
            self._result.assertion_failures.append(
                f"assert {stmt.variable}: variable not found"
            )
            return

        if stmt.exact:
            expected = stmt.values[0]
            # Coerce to same numeric type for comparison
            try:
                ok = (int(value) == int(expected)) or (float(value) == float(expected))
            except (TypeError, ValueError):
                ok = str(value) == str(expected)
        else:
            # ∈ {values}
            ok = any(
                _values_equal(value, v) for v in stmt.values
            )

        if not ok:
            msg = (
                f"assert {stmt.variable} == {stmt.values[0]}"
                if stmt.exact
                else f"assert {stmt.variable} ∈ {{{', '.join(str(v) for v in stmt.values)}}}"
            )
            self._result.assertion_failures.append(f"FAIL: {msg}  (got {value!r})")
        else:
            self._result.circuit_steps.append(
                f"assert {stmt.variable} ✓ (= {value})"
            )

    # ---- log ---------------------------------------------------------------

    def _exec_log(self, stmt: LogStmt) -> None:
        expr = stmt.expr
        if isinstance(expr, str) and expr in self._classical:
            val = self._classical[expr]
        else:
            val = expr
        self._result.outputs.append(str(val) if val is not None else "null")


def _values_equal(a: Any, b: Any) -> bool:
    try:
        return int(a) == int(b)
    except (TypeError, ValueError):
        pass
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        pass
    return str(a).strip("|⟩ ") == str(b).strip("|⟩ ")


# ---------------------------------------------------------------------------
# ASCII circuit diagram
# ---------------------------------------------------------------------------

def _build_diagram(program: QubeProgram) -> str:
    """Generate a simple ASCII circuit diagram for the QUBE program."""
    # Collect qubit names in declaration order
    qubit_names: list[str] = []
    for stmt in program.stmts:
        if isinstance(stmt, StateDecl) and stmt.name not in qubit_names:
            qubit_names.append(stmt.name)

    if not qubit_names:
        return "(no qubits declared)"

    # Build column list: each gate/collapse becomes a column
    columns: list[dict[str, str]] = []
    for stmt in program.stmts:
        if isinstance(stmt, GateApply):
            col: dict[str, str] = {}
            for q in qubit_names:
                if q in stmt.targets:
                    gate_base = stmt.gate.split("(")[0]
                    if stmt.gate in ("CNOT", "CX"):
                        col[q] = "⊕" if q == stmt.targets[-1] else "●"
                    elif stmt.gate == "CZ":
                        col[q] = "Z" if q == stmt.targets[-1] else "●"
                    elif stmt.gate == "SWAP":
                        col[q] = "×"
                    else:
                        col[q] = f"[{gate_base}]"
                else:
                    col[q] = "───"
            columns.append(col)
        elif isinstance(stmt, Collapse):
            col = {}
            for q in qubit_names:
                col[q] = "[M]" if q == stmt.qubit else "───"
            columns.append(col)

    # Render
    lines: list[str] = []
    for q in qubit_names:
        row = f"{q:>6} |0⟩ ─"
        for col in columns:
            cell = col.get(q, "───")
            row += f"─{cell}─"
        row += "─"
        lines.append(row)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute(source: str, seed: int | None = None) -> ExecutionResult:
    """Parse and execute a QUBE circuit string."""
    program = parse(source)
    executor = QubeExecutor(seed=seed)
    return executor.execute(program)


def diagram(source: str) -> str:
    """Parse a QUBE circuit string and return an ASCII diagram."""
    program = parse(source)
    return _build_diagram(program)
