"""Tests for the QUBE statevector executor."""

import unittest

from aeonmi_claude_connector.qube_executor import ExecutionResult, diagram, execute


# ---------------------------------------------------------------------------
# Pure state execution
# ---------------------------------------------------------------------------

class TestPureStates(unittest.TestCase):
    def test_zero_state_collapses_to_zero(self):
        for seed in range(10):
            result = execute("state q = |0⟩\ncollapse q -> r\nlog(r)", seed=seed)
            self.assertEqual(result.measurements["r"], 0)

    def test_one_state_collapses_to_one(self):
        for seed in range(10):
            result = execute("state q = |1⟩\ncollapse q -> r\nlog(r)", seed=seed)
            self.assertEqual(result.measurements["r"], 1)

    def test_result_type_is_execution_result(self):
        result = execute("state q = |0⟩\ncollapse q -> r")
        self.assertIsInstance(result, ExecutionResult)


# ---------------------------------------------------------------------------
# Hadamard gate
# ---------------------------------------------------------------------------

class TestHadamard(unittest.TestCase):
    SOURCE = "state q = |0⟩\napply H -> q\ncollapse q -> r\nassert r ∈ {0, 1}\nlog(r)"

    def test_outcome_in_zero_or_one(self):
        for seed in range(20):
            result = execute(self.SOURCE, seed=seed)
            self.assertIn(result.measurements["r"], {0, 1})

    def test_both_outcomes_occur(self):
        outcomes = set()
        for seed in range(100):
            result = execute(self.SOURCE, seed=seed)
            outcomes.add(result.measurements["r"])
        self.assertEqual(outcomes, {0, 1})

    def test_no_assertion_failures(self):
        result = execute(self.SOURCE, seed=42)
        self.assertEqual(result.assertion_failures, [])


# ---------------------------------------------------------------------------
# X gate (bit flip)
# ---------------------------------------------------------------------------

class TestXGate(unittest.TestCase):
    SOURCE = "state q = |0⟩\napply X -> q\ncollapse q -> r\nassert r == 1\nlog(r)"

    def test_x_flips_to_one(self):
        for seed in range(10):
            result = execute(self.SOURCE, seed=seed)
            self.assertEqual(result.measurements["r"], 1)

    def test_no_assertion_failures(self):
        result = execute(self.SOURCE, seed=0)
        self.assertEqual(result.assertion_failures, [])


# ---------------------------------------------------------------------------
# CNOT / Bell state
# ---------------------------------------------------------------------------

class TestCNOT(unittest.TestCase):
    BELL = (
        "state q0 = |0⟩\n"
        "state q1 = |0⟩\n"
        "apply H -> q0\n"
        "apply CNOT(q0, q1)\n"
        "collapse q0 -> r0\n"
        "collapse q1 -> r1\n"
        "assert r0 ∈ {0, 1}\n"
        "assert r1 ∈ {0, 1}\n"
        "log(r0)\n"
        "log(r1)"
    )

    def test_bell_both_same(self):
        """Bell pair always collapses to the same bit."""
        for seed in range(30):
            result = execute(self.BELL, seed=seed)
            self.assertEqual(result.measurements["r0"], result.measurements["r1"],
                             f"seed={seed}: r0={result.measurements['r0']}, r1={result.measurements['r1']}")

    def test_bell_no_assertion_failures(self):
        result = execute(self.BELL, seed=7)
        self.assertEqual(result.assertion_failures, [])

    def test_bell_has_two_outputs(self):
        result = execute(self.BELL, seed=0)
        self.assertEqual(len(result.outputs), 2)


# ---------------------------------------------------------------------------
# Assert pass / fail
# ---------------------------------------------------------------------------

class TestAssertPass(unittest.TestCase):
    def test_assert_pass_not_in_failures(self):
        src = "state q = |1⟩\ncollapse q -> r\nassert r == 1"
        result = execute(src, seed=0)
        self.assertEqual(result.assertion_failures, [])

    def test_assert_member_pass(self):
        src = "state q = |0⟩\ncollapse q -> r\nassert r ∈ {0, 1}"
        result = execute(src, seed=0)
        self.assertEqual(result.assertion_failures, [])


class TestAssertFail(unittest.TestCase):
    def test_assert_fail_recorded(self):
        # |0⟩ always collapses to 0, so assert r == 1 should fail
        src = "state q = |0⟩\ncollapse q -> r\nassert r == 1"
        result = execute(src, seed=0)
        self.assertEqual(len(result.assertion_failures), 1)
        self.assertIn("FAIL", result.assertion_failures[0])

    def test_assert_member_fail(self):
        # |1⟩ always collapses to 1, so assert r ∈ {0} should fail
        src = "state q = |1⟩\ncollapse q -> r\nassert r ∈ {0}"
        result = execute(src, seed=0)
        self.assertEqual(len(result.assertion_failures), 1)


# ---------------------------------------------------------------------------
# Log output
# ---------------------------------------------------------------------------

class TestLog(unittest.TestCase):
    def test_log_appears_in_outputs(self):
        src = "state q = |0⟩\ncollapse q -> r\nlog(r)"
        result = execute(src, seed=0)
        self.assertEqual(len(result.outputs), 1)
        self.assertIn("0", result.outputs[0])

    def test_print_alias(self):
        src = "state q = |1⟩\ncollapse q -> r\nprint(r)"
        result = execute(src, seed=0)
        self.assertEqual(len(result.outputs), 1)
        self.assertIn("1", result.outputs[0])

    def test_multiple_logs(self):
        src = "state q0 = |0⟩\nstate q1 = |1⟩\ncollapse q0 -> r0\ncollapse q1 -> r1\nlog(r0)\nlog(r1)"
        result = execute(src, seed=0)
        self.assertEqual(len(result.outputs), 2)


# ---------------------------------------------------------------------------
# Circuit diagram
# ---------------------------------------------------------------------------

class TestDiagram(unittest.TestCase):
    BELL = (
        "state q0 = |0⟩\n"
        "state q1 = |0⟩\n"
        "apply H -> q0\n"
        "apply CNOT(q0, q1)\n"
        "collapse q0 -> r0\n"
        "collapse q1 -> r1"
    )

    def test_diagram_non_empty(self):
        d = diagram(self.BELL)
        self.assertIsInstance(d, str)
        self.assertGreater(len(d), 0)

    def test_diagram_contains_qubit_names(self):
        d = diagram(self.BELL)
        self.assertIn("q0", d)
        self.assertIn("q1", d)

    def test_single_qubit_diagram(self):
        d = diagram("state q = |0⟩\napply H -> q\ncollapse q -> r")
        self.assertIn("q", d)

    def test_no_qubits(self):
        d = diagram("log(42)")
        self.assertIn("no qubits", d.lower())


# ---------------------------------------------------------------------------
# Deterministic seed
# ---------------------------------------------------------------------------

class TestSeed(unittest.TestCase):
    SOURCE = "state q = |0⟩\napply H -> q\ncollapse q -> r"

    def test_same_seed_same_outcome(self):
        r1 = execute(self.SOURCE, seed=12345)
        r2 = execute(self.SOURCE, seed=12345)
        self.assertEqual(r1.measurements["r"], r2.measurements["r"])

    def test_different_seeds_can_differ(self):
        outcomes = set()
        for seed in range(100):
            r = execute(self.SOURCE, seed=seed)
            outcomes.add(r.measurements["r"])
        self.assertEqual(outcomes, {0, 1})


# ---------------------------------------------------------------------------
# circuit_steps
# ---------------------------------------------------------------------------

class TestCircuitSteps(unittest.TestCase):
    def test_steps_non_empty(self):
        src = "state q = |0⟩\napply H -> q\ncollapse q -> r"
        result = execute(src, seed=0)
        self.assertGreater(len(result.circuit_steps), 0)

    def test_to_dict_keys(self):
        src = "state q = |0⟩\ncollapse q -> r"
        d = execute(src, seed=0).to_dict()
        self.assertIn("outputs", d)
        self.assertIn("measurements", d)
        self.assertIn("assertion_failures", d)
        self.assertIn("circuit_steps", d)


if __name__ == "__main__":
    unittest.main()
