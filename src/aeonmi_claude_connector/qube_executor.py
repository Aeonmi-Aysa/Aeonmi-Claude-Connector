"""QUBE workflow executor / interpreter.

Walks the AST produced by qube_parser and evaluates each node, maintaining
an environment of bindings and an entropy-credit ledger.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any

from .qube_parser import (
    Binding, Bottom, Call, Collapse, ConstructorCall, Consume,
    EntropyCredit, Entanglement, Evolution, FlowPipe, GlyphLock,
    Identifier, Infinity, Join, Node, Number, Program, Psi,
    QuantumState, StringLiteral, Superposition, Yields,
)


# ---------------------------------------------------------------------------
# Runtime value types
# ---------------------------------------------------------------------------

@dataclass
class QValue:
    """Base class for all QUBE runtime values."""


@dataclass
class QScalar(QValue):
    """A classical (collapsed) scalar — number or string."""
    value: Any

    def __repr__(self) -> str:
        return repr(self.value)


@dataclass
class QState(QValue):
    """A quantum state |label⟩ with an associated amplitude (1.0 by default)."""
    label: Any
    amplitude: float = 1.0

    def __repr__(self) -> str:
        return f"|{self.label}⟩(amp={self.amplitude:.3f})"


@dataclass
class QSuperposition(QValue):
    """A superposition of several (state, weight) pairs."""
    branches: list[tuple[QValue, float]] = field(default_factory=list)

    def __repr__(self) -> str:
        parts = " ⊕ ".join(f"{v!r}@{w:.3f}" for v, w in self.branches)
        return f"({parts})"


@dataclass
class QEntangled(QValue):
    """Two values joined by ⊗."""
    left: QValue
    right: QValue

    def __repr__(self) -> str:
        return f"({self.left!r} ⊗ {self.right!r})"


@dataclass
class QConstructor(QValue):
    """Aeonmi Constructor AI node."""
    memory: list[QValue] = field(default_factory=list)
    locked: bool = False

    def __repr__(self) -> str:
        lock = "◈" if self.locked else ""
        return f"Æ{lock}[mem={len(self.memory)}]"


@dataclass
class QInfinity(QValue):
    def __repr__(self) -> str:
        return "∞"


@dataclass
class QBottom(QValue):
    def __repr__(self) -> str:
        return "⊥"


@dataclass
class QFlow(QValue):
    """A composed flow: source ↝ target."""
    source: QValue
    target: QValue

    def __repr__(self) -> str:
        return f"({self.source!r} ↝ {self.target!r})"


@dataclass
class QEvolution(QValue):
    """A self-evolving value that changes each time it is observed."""
    seed: QValue
    generation: int = 0

    def __repr__(self) -> str:
        return f"⟳{self.seed!r}@gen{self.generation}"


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

class Environment:
    def __init__(self, parent: Environment | None = None) -> None:
        self._bindings: dict[str, QValue] = {}
        self._parent = parent

    def get(self, name: str) -> QValue:
        if name in self._bindings:
            return self._bindings[name]
        if self._parent:
            return self._parent.get(name)
        raise NameError(f"Unbound name: {name!r}")

    def set(self, name: str, value: QValue) -> None:
        self._bindings[name] = value

    def all_bindings(self) -> dict[str, QValue]:
        result: dict[str, QValue] = {}
        if self._parent:
            result.update(self._parent.all_bindings())
        result.update(self._bindings)
        return result


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

class ExecutionResult:
    def __init__(self) -> None:
        self.outputs: list[str] = []
        self.bindings: dict[str, str] = {}
        self.entropy_credits: float = 0.0
        self.collapsed_values: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "outputs": self.outputs,
            "bindings": self.bindings,
            "entropy_credits": self.entropy_credits,
            "collapsed_values": self.collapsed_values,
        }


class QubeExecutor:
    """Interprets a QUBE AST and returns an :class:`ExecutionResult`."""

    EVOLUTION_DEPTH = 3   # default self-evolution steps

    def __init__(self, seed: int | None = None) -> None:
        self._env = Environment()
        self._entropy: float = 0.0
        self._rng = random.Random(seed)
        self._result = ExecutionResult()

    # ---- public ------------------------------------------------------------

    def execute(self, program: Program) -> ExecutionResult:
        for stmt in program.statements:
            val = self._eval(stmt)
            if not isinstance(stmt, Binding):
                self._result.outputs.append(repr(val))
        self._result.bindings = {k: repr(v) for k, v in self._env.all_bindings().items()}
        self._result.entropy_credits = self._entropy
        return self._result

    # ---- node dispatch -----------------------------------------------------

    def _eval(self, node: Node) -> QValue:
        method = "_eval_" + type(node).__name__.lower()
        handler = getattr(self, method, None)
        if handler is None:
            raise NotImplementedError(f"No handler for node type {type(node).__name__}")
        return handler(node)

    def _eval_program(self, node: Program) -> QValue:
        last: QValue = QBottom()
        for stmt in node.statements:
            last = self._eval(stmt)
        return last

    def _eval_binding(self, node: Binding) -> QValue:
        val = self._eval(node.value)
        self._env.set(node.name, val)
        return val

    def _eval_entanglement(self, node: Entanglement) -> QValue:
        left = self._eval(node.left)
        right = self._eval(node.right)
        return QEntangled(left=left, right=right)

    def _eval_superposition(self, node: Superposition) -> QValue:
        left = self._eval(node.left)
        right = self._eval(node.right)
        branches: list[tuple[QValue, float]] = []
        # Flatten nested superpositions
        for src in (left, right):
            if isinstance(src, QSuperposition):
                branches.extend(src.branches)
            else:
                branches.append((src, 1.0))
        # Normalize weights
        total = sum(w for _, w in branches)
        branches = [(v, w / total) for v, w in branches]
        return QSuperposition(branches=branches)

    def _eval_collapse(self, node: Collapse) -> QValue:
        val = self._eval(node.state)
        collapsed = self._collapse(val)
        self._result.collapsed_values.append(repr(collapsed))
        return collapsed

    def _collapse(self, val: QValue) -> QValue:
        if isinstance(val, QSuperposition):
            weights = [w for _, w in val.branches]
            chosen, _ = self._rng.choices(val.branches, weights=weights, k=1)[0]
            return self._collapse(chosen)
        if isinstance(val, QState):
            inner = val.label
            if isinstance(inner, QValue):
                return self._collapse(inner)
            return QScalar(inner)
        if isinstance(val, QEntangled):
            return QEntangled(
                left=self._collapse(val.left),
                right=self._collapse(val.right),
            )
        if isinstance(val, QEvolution):
            return self._collapse(val.seed)
        return val

    def _eval_evolution(self, node: Evolution) -> QValue:
        seed = self._eval(node.body)
        return QEvolution(seed=seed)

    def _eval_glyphlock(self, node: GlyphLock) -> QValue:
        val = self._eval(node.expr)
        if isinstance(val, QConstructor):
            val.locked = True
            return val
        # Wrap in a single-branch superposition to mark as locked
        locked = QSuperposition(branches=[(val, 1.0)])
        return locked

    def _eval_flowpipe(self, node: FlowPipe) -> QValue:
        source = self._eval(node.source)
        # Bring evolution forward
        if isinstance(source, QEvolution):
            source = QEvolution(seed=source.seed, generation=source.generation + 1)
        target_val = self._eval(node.target)
        return QFlow(source=source, target=target_val)

    def _eval_quantumstate(self, node: QuantumState) -> QValue:
        content = self._eval(node.content)
        if isinstance(content, QScalar):
            return QState(label=content.value)
        return QState(label=content)

    def _eval_constructorcall(self, node: ConstructorCall) -> QValue:
        args = [self._eval(a) for a in node.args]
        return QConstructor(memory=args)

    def _eval_infinity(self, _: Infinity) -> QValue:
        return QInfinity()

    def _eval_bottom(self, _: Bottom) -> QValue:
        return QBottom()

    def _eval_psi(self, _: Psi) -> QValue:
        return QState(label="ψ")

    def _eval_entropycredit(self, node: EntropyCredit) -> QValue:
        amount_val = self._eval(node.amount)
        amount = amount_val.value if isinstance(amount_val, QScalar) else 1.0
        self._entropy += float(amount)
        return QScalar(amount)

    def _eval_consume(self, node: Consume) -> QValue:
        val = self._eval(node.expr)
        # Remove from environment if it is a bound identifier
        return self._collapse(val)

    def _eval_yields(self, node: Yields) -> QValue:
        ctx = self._eval(node.context)
        result = self._eval(node.result)
        return QEntangled(left=ctx, right=result)

    def _eval_join(self, node: Join) -> QValue:
        left = self._eval(node.left)
        right = self._eval(node.right)
        merged: list[tuple[QValue, float]] = []
        for v in (left, right):
            if isinstance(v, QSuperposition):
                merged.extend(v.branches)
            else:
                merged.append((v, 1.0))
        total = sum(w for _, w in merged)
        merged = [(v, w / total) for v, w in merged]
        return QSuperposition(branches=merged)

    def _eval_call(self, node: Call) -> QValue:
        # Built-in functions
        args = [self._eval(a) for a in node.args]
        if node.name == "amplitude":
            if args and isinstance(args[0], QState):
                return QScalar(args[0].amplitude)
            return QScalar(1.0)
        if node.name == "sqrt":
            val = args[0].value if isinstance(args[0], QScalar) else 1.0
            return QScalar(math.sqrt(float(val)))
        if node.name == "abs":
            val = args[0].value if isinstance(args[0], QScalar) else 0.0
            return QScalar(abs(float(val)))
        # Unknown call — return a labelled state
        return QState(label=f"{node.name}({', '.join(repr(a) for a in args)})")

    def _eval_identifier(self, node: Identifier) -> QValue:
        return self._env.get(node.name)

    def _eval_number(self, node: Number) -> QValue:
        return QScalar(node.value)

    def _eval_stringliteral(self, node: StringLiteral) -> QValue:
        return QScalar(node.value)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute(source: str, seed: int | None = None) -> ExecutionResult:
    """Parse and execute *source* QUBE code, returning an :class:`ExecutionResult`."""
    from .qube_parser import parse  # local import to avoid circular deps at module level
    program = parse(source)
    executor = QubeExecutor(seed=seed)
    return executor.execute(program)
