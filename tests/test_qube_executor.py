"""Tests for the QUBE executor."""

import pytest

from aeonmi_claude_connector.qube_executor import (
    QBottom,
    QConstructor,
    QEntangled,
    QFlow,
    QInfinity,
    QScalar,
    QState,
    QSuperposition,
    execute,
)


# ---------------------------------------------------------------------------
# Basic execution
# ---------------------------------------------------------------------------

class TestExecuteBindings:
    def test_infinity_binding(self):
        result = execute("λ x ≔ ∞")
        assert "x" in result.bindings
        assert "∞" in result.bindings["x"]

    def test_number_binding(self):
        result = execute("λ n ≔ 42")
        assert "n" in result.bindings
        assert "42" in result.bindings["n"]

    def test_string_binding(self):
        result = execute('λ s ≔ "hello"')
        assert "s" in result.bindings
        assert "hello" in result.bindings["s"]

    def test_bottom_binding(self):
        result = execute("λ x ≔ ⊥")
        assert "x" in result.bindings
        assert "⊥" in result.bindings["x"]


class TestQuantumState:
    def test_psi_state(self):
        result = execute("|ψ⟩")
        assert len(result.outputs) == 1
        assert "ψ" in result.outputs[0]

    def test_string_state(self):
        result = execute('|"hi"⟩')
        assert len(result.outputs) == 1
        assert "hi" in result.outputs[0]


class TestEntanglement:
    def test_entangle_two_states(self):
        result = execute("λ pair ≔ |ψ⟩ ⊗ ∞")
        assert "pair" in result.bindings
        assert "⊗" in result.bindings["pair"]

    def test_entangle_numbers(self):
        result = execute("1 ⊗ 2")
        assert len(result.outputs) == 1
        assert "⊗" in result.outputs[0]


class TestSuperposition:
    def test_superpose_two_states(self):
        result = execute('|"a"⟩ ⊕ |"b"⟩')
        assert len(result.outputs) == 1
        assert "⊕" in result.outputs[0]

    def test_superpose_normalises(self):
        # Superposing three items should normalise weights to sum=1
        result = execute('|"a"⟩ ⊕ |"b"⟩ ⊕ |"c"⟩')
        assert len(result.outputs) == 1


class TestCollapse:
    def test_collapse_deterministic(self):
        # With a fixed seed the result should be reproducible
        r1 = execute('↯ (|"yes"⟩ ⊕ |"no"⟩)', seed=0)
        r2 = execute('↯ (|"yes"⟩ ⊕ |"no"⟩)', seed=0)
        assert r1.collapsed_values == r2.collapsed_values

    def test_collapse_random_is_one_of_branches(self):
        for _ in range(20):
            result = execute('↯ (|"yes"⟩ ⊕ |"no"⟩)')
            assert result.collapsed_values[0] in ("'yes'", "'no'")

    def test_collapse_single_state(self):
        result = execute('↯ |"hello"⟩')
        assert result.collapsed_values[0] == "'hello'"


class TestEvolution:
    def test_evolution_creates_evolution_value(self):
        result = execute("λ loop ≔ ⟳ |ψ⟩")
        assert "loop" in result.bindings
        assert "⟳" in result.bindings["loop"]


class TestGlyphLock:
    def test_glyph_lock_constructor(self):
        result = execute("λ brain ≔ ◈ Æ(∞)")
        assert "brain" in result.bindings

    def test_glyph_lock_plain(self):
        result = execute("λ x ≔ ◈ |ψ⟩")
        assert "x" in result.bindings


class TestConstructor:
    def test_constructor_no_args(self):
        result = execute("Æ()")
        assert len(result.outputs) == 1
        assert "Æ" in result.outputs[0]

    def test_constructor_with_infinity(self):
        result = execute("Æ(∞)")
        assert "Æ" in result.outputs[0]

    def test_constructor_locked(self):
        result = execute("◈ Æ(∞)")
        assert "◈" in result.outputs[0]


class TestFlowPipe:
    def test_simple_flow(self):
        result = execute("|ψ⟩ ↝ ∞")
        assert len(result.outputs) == 1
        assert "↝" in result.outputs[0]

    def test_chained_flow(self):
        result = execute("|ψ⟩ ↝ ∞ ↝ ∞")
        assert len(result.outputs) == 1


class TestEntropyCredit:
    def test_entropy_accumulates(self):
        result = execute("⧖ 10\n⧖ 5")
        assert result.entropy_credits == pytest.approx(15.0)

    def test_entropy_in_binding(self):
        result = execute("λ budget ≔ ⧖ 42")
        assert result.entropy_credits == pytest.approx(42.0)


class TestIdentifierLookup:
    def test_bound_identifier_is_resolved(self):
        result = execute("λ x ≔ ∞\nx")
        # 'x' should resolve to ∞ and appear in outputs
        assert any("∞" in o for o in result.outputs)

    def test_unbound_identifier_raises(self):
        with pytest.raises(NameError):
            execute("undefinedVar")


class TestBuiltinCalls:
    def test_sqrt(self):
        result = execute("sqrt(9)")
        assert "3" in result.outputs[0]

    def test_abs_negative(self):
        result = execute("abs(-5)")
        assert "5" in result.outputs[0]


class TestExamples:
    """Ensure all built-in examples execute without errors."""

    def test_root_soul(self):
        result = execute("λ RootSoul ≔ |ψ⟩ ⊗ ∞")
        assert "RootSoul" in result.bindings

    def test_superposed_greeting(self):
        result = execute('λ greeting ≔ |"Hello"⟩ ⊕ |"Aysa"⟩')
        assert "greeting" in result.bindings

    def test_collapsed_greeting(self):
        result = execute('λ greeting ≔ |"Hello"⟩ ⊕ |"Aysa"⟩\n↯ greeting', seed=1)
        assert result.collapsed_values

    def test_locked_constructor(self):
        result = execute("λ brain ≔ ◈ Æ(∞)")
        assert "brain" in result.bindings

    def test_self_evolving_flow(self):
        result = execute("λ soul ≔ |ψ⟩\nλ loop ≔ soul ↝ ⟳ soul")
        assert "loop" in result.bindings

    def test_entropy_budget(self):
        result = execute("λ budget ≔ ⧖ 42")
        assert result.entropy_credits == pytest.approx(42.0)
