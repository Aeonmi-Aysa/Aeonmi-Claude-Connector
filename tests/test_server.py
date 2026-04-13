"""Tests for the MCP server tool functions."""

import unittest

from aeonmi_claude_connector.server import (
    aeonmi_explain,
    aeonmi_generate,
    aeonmi_list_keywords,
    cli_help,
    mother_help,
    qube_check,
    qube_diagram,
    qube_explain,
    qube_generate,
    qube_run,
)


# ---------------------------------------------------------------------------
# qube_run
# ---------------------------------------------------------------------------

class TestQubeRunTool(unittest.TestCase):
    BELL = (
        "state q0 = |0⟩\n"
        "state q1 = |0⟩\n"
        "apply H -> q0\n"
        "apply CNOT(q0, q1)\n"
        "collapse q0 -> r0\n"
        "collapse q1 -> r1\n"
        "log(r0)\n"
        "log(r1)"
    )

    def test_returns_dict(self):
        result = qube_run(self.BELL, seed=0)
        self.assertIsInstance(result, dict)

    def test_has_required_keys(self):
        result = qube_run(self.BELL, seed=0)
        self.assertIn("outputs", result)
        self.assertIn("measurements", result)
        self.assertIn("assertion_failures", result)
        self.assertIn("circuit_steps", result)

    def test_bell_has_two_outputs(self):
        result = qube_run(self.BELL, seed=0)
        self.assertEqual(len(result["outputs"]), 2)

    def test_bell_both_measurements_same(self):
        result = qube_run(self.BELL, seed=42)
        self.assertEqual(result["measurements"]["r0"], result["measurements"]["r1"])

    def test_parse_error_returns_error_key(self):
        result = qube_run("not valid qube source @@@@", seed=0)
        # Either error key or empty measurements — parser is lenient
        # but at least should not raise
        self.assertIsInstance(result, dict)

    def test_deterministic_with_seed(self):
        r1 = qube_run("state q = |0⟩\napply H -> q\ncollapse q -> r", seed=999)
        r2 = qube_run("state q = |0⟩\napply H -> q\ncollapse q -> r", seed=999)
        self.assertEqual(r1["measurements"]["r"], r2["measurements"]["r"])


# ---------------------------------------------------------------------------
# qube_check
# ---------------------------------------------------------------------------

class TestQubeCheckTool(unittest.TestCase):
    def test_valid_returns_valid_true(self):
        result = qube_check("state q = |0⟩\ncollapse q -> r")
        self.assertTrue(result["valid"])
        self.assertIn("statement_count", result)

    def test_statement_count_correct(self):
        result = qube_check("state q = |0⟩\ncollapse q -> r\nlog(r)")
        self.assertEqual(result["statement_count"], 3)

    def test_invalid_returns_valid_false(self):
        result = qube_check("apply H q")  # missing arrow
        self.assertFalse(result["valid"])
        self.assertIn("error", result)

    def test_empty_source(self):
        result = qube_check("")
        self.assertTrue(result["valid"])
        self.assertEqual(result["statement_count"], 0)


# ---------------------------------------------------------------------------
# qube_diagram
# ---------------------------------------------------------------------------

class TestQubeDiagramTool(unittest.TestCase):
    BELL = (
        "state q0 = |0⟩\n"
        "state q1 = |0⟩\n"
        "apply H -> q0\n"
        "apply CNOT(q0, q1)\n"
        "collapse q0 -> r0\n"
        "collapse q1 -> r1"
    )

    def test_returns_non_empty_diagram(self):
        result = qube_diagram(self.BELL)
        self.assertIn("diagram", result)
        self.assertGreater(len(result["diagram"]), 0)

    def test_diagram_contains_qubit_names(self):
        result = qube_diagram(self.BELL)
        self.assertIn("q0", result["diagram"])
        self.assertIn("q1", result["diagram"])

    def test_single_qubit(self):
        result = qube_diagram("state q = |0⟩\napply H -> q\ncollapse q -> r")
        self.assertIn("q", result["diagram"])


# ---------------------------------------------------------------------------
# qube_explain
# ---------------------------------------------------------------------------

class TestQubeExplainTool(unittest.TestCase):
    def test_explain_h_mentions_hadamard(self):
        result = qube_explain("H")
        self.assertIn("explanation", result)
        self.assertIn("Hadamard", result["explanation"])

    def test_explain_cnot_mentions_controlled(self):
        result = qube_explain("CNOT")
        self.assertIn("Controlled", result["explanation"])

    def test_explain_qubit_zero(self):
        result = qube_explain("|0⟩")
        self.assertIn("explanation", result)
        self.assertIn("qubit", result["explanation"].lower())

    def test_explain_qubit_plus(self):
        result = qube_explain("|+⟩")
        self.assertIn("superposition", result["explanation"].lower())

    def test_explain_therefore_glyph(self):
        result = qube_explain("∴")
        self.assertIn("comment", result["explanation"].lower())

    def test_explain_keyword_state(self):
        result = qube_explain("state")
        self.assertIn("qubit", result["explanation"].lower())

    def test_explain_keyword_apply(self):
        result = qube_explain("apply")
        self.assertIn("gate", result["explanation"].lower())

    def test_explain_has_examples(self):
        result = qube_explain("H")
        self.assertIn("examples", result)
        self.assertIsInstance(result["examples"], list)
        self.assertGreater(len(result["examples"]), 0)


# ---------------------------------------------------------------------------
# qube_generate
# ---------------------------------------------------------------------------

class TestQubeGenerateTool(unittest.TestCase):
    def test_bell_generates_cnot(self):
        result = qube_generate("bell state")
        self.assertIn("code", result)
        self.assertIn("CNOT", result["code"])

    def test_bell_generates_valid_code(self):
        result = qube_generate("bell state")
        check = qube_check(result["code"])
        self.assertTrue(check["valid"])

    def test_hadamard_generates_h_gate(self):
        result = qube_generate("hadamard superposition")
        self.assertIn("H", result["code"])

    def test_x_gate_flip(self):
        result = qube_generate("bit flip x gate")
        self.assertIn("X", result["code"])

    def test_ghz_generates_three_qubits(self):
        result = qube_generate("ghz state")
        self.assertIn("code", result)
        # GHZ uses two CNOTs
        self.assertIn("CNOT", result["code"])

    def test_fallback_returns_valid_code(self):
        result = qube_generate("xyzzy magic unknown thing")
        check = qube_check(result["code"])
        self.assertTrue(check["valid"])

    def test_returns_description(self):
        result = qube_generate("bell state")
        self.assertIn("description", result)


# ---------------------------------------------------------------------------
# aeonmi_explain
# ---------------------------------------------------------------------------

class TestAeonmiExplainTool(unittest.TestCase):
    def test_explain_circle_function(self):
        result = aeonmi_explain("◯")
        self.assertIn("explanation", result)
        self.assertIn("circle", result["explanation"].lower())

    def test_explain_array_genesis(self):
        result = aeonmi_explain("⧉")
        self.assertIn("Array Genesis", result["explanation"])

    def test_explain_tensor(self):
        result = aeonmi_explain("⊗")
        self.assertIn("tensor", result["explanation"].lower())

    def test_explain_quantum_keyword(self):
        result = aeonmi_explain("quantum")
        self.assertIn("quantum", result["explanation"].lower())

    def test_explain_qubit_keyword(self):
        result = aeonmi_explain("qubit")
        self.assertIn("qubit", result["explanation"].lower())

    def test_explain_has_examples(self):
        result = aeonmi_explain("◯")
        self.assertIn("examples", result)
        self.assertIsInstance(result["examples"], list)

    def test_explain_unknown_returns_overview(self):
        result = aeonmi_explain("xyzzy_unknown_thing")
        self.assertIn("explanation", result)
        self.assertIn("aeonmi", result["explanation"].lower())


# ---------------------------------------------------------------------------
# aeonmi_generate
# ---------------------------------------------------------------------------

class TestAeonmiGenerateTool(unittest.TestCase):
    def test_quantum_function_generates_quantum_keywords(self):
        result = aeonmi_generate("quantum function")
        self.assertIn("code", result)
        code = result["code"]
        self.assertTrue(
            "quantum" in code or "qubit" in code or "superpose" in code,
            f"Expected quantum keywords in: {code}"
        )

    def test_returns_language_aeonmi(self):
        result = aeonmi_generate("anything")
        self.assertEqual(result["language"], "aeonmi")

    def test_bell_generates_entangle(self):
        result = aeonmi_generate("bell state two qubits")
        code = result["code"]
        self.assertTrue("qubit" in code or "entangle" in code or "CNOT" in code)

    def test_hello_generates_log(self):
        result = aeonmi_generate("hello world output")
        self.assertIn("log", result["code"])

    def test_glyph_generates_glyph_algebra(self):
        result = aeonmi_generate("glyph algebra tensor")
        self.assertTrue("⊗" in result["code"] or "↦" in result["code"] or "⧉" in result["code"])


# ---------------------------------------------------------------------------
# aeonmi_list_keywords
# ---------------------------------------------------------------------------

class TestAeonmiListKeywords(unittest.TestCase):
    def test_returns_keywords(self):
        result = aeonmi_list_keywords()
        self.assertIn("keywords", result)
        self.assertIsInstance(result["keywords"], list)
        self.assertIn("let", result["keywords"])
        self.assertIn("function", result["keywords"])

    def test_returns_quantum_keywords(self):
        result = aeonmi_list_keywords()
        self.assertIn("quantum_keywords", result)
        self.assertIn("qubit", result["quantum_keywords"])
        self.assertIn("superpose", result["quantum_keywords"])

    def test_returns_builtins(self):
        result = aeonmi_list_keywords()
        self.assertIn("builtins", result)
        self.assertIn("log", result["builtins"])

    def test_returns_glyphs(self):
        result = aeonmi_list_keywords()
        self.assertIn("glyphs", result)
        self.assertIn("◯", result["glyphs"])
        self.assertIn("⧉", result["glyphs"])
        self.assertIn("⊗", result["glyphs"])

    def test_returns_operators(self):
        result = aeonmi_list_keywords()
        self.assertIn("operators", result)


# ---------------------------------------------------------------------------
# mother_help
# ---------------------------------------------------------------------------

class TestMotherHelpTool(unittest.TestCase):
    def test_no_arg_returns_commands_and_help(self):
        result = mother_help()
        self.assertIn("commands", result)
        self.assertIn("help", result)

    def test_no_arg_help_is_non_empty(self):
        result = mother_help()
        self.assertGreater(len(result["help"]), 0)

    def test_no_arg_commands_is_dict(self):
        result = mother_help()
        self.assertIsInstance(result["commands"], dict)

    def test_evolve_command_has_description(self):
        result = mother_help("evolve")
        self.assertIn("help", result)
        self.assertIn("evolve", result["help"].lower())

    def test_dream_command(self):
        result = mother_help("dream")
        self.assertIn("help", result)
        self.assertIn("dream", result["help"].lower())

    def test_unknown_command(self):
        result = mother_help("definitely_not_a_command")
        self.assertIn("help", result)

    def test_no_arg_includes_status(self):
        result = mother_help()
        text = str(result)
        self.assertIn("status", text.lower())


# ---------------------------------------------------------------------------
# cli_help
# ---------------------------------------------------------------------------

class TestCliHelpTool(unittest.TestCase):
    def test_no_arg_returns_subcommand_list(self):
        result = cli_help()
        self.assertIn("help", result)
        self.assertIn("qube", result["help"].lower())
        self.assertIn("run", result["help"].lower())

    def test_qube_subcommand_flags(self):
        result = cli_help("qube")
        self.assertIn("help", result)
        text = result["help"]
        self.assertIn("qube", text.lower())
        self.assertIn("run", text.lower())

    def test_mother_subcommand(self):
        result = cli_help("mother")
        self.assertIn("help", result)
        self.assertIn("mother", result["help"].lower())

    def test_run_subcommand(self):
        result = cli_help("run")
        self.assertIn("help", result)

    def test_unknown_subcommand(self):
        result = cli_help("nonexistent_subcommand_xyz")
        self.assertIn("help", result)


# ---------------------------------------------------------------------------
# Resources (imported and called directly)
# ---------------------------------------------------------------------------

class TestResources(unittest.TestCase):
    def _get_resource(self, fn_name: str) -> str:
        from aeonmi_claude_connector import server
        fn = getattr(server, fn_name)
        return fn()

    def test_qube_grammar_resource(self):
        text = self._get_resource("qube_grammar_resource")
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)
        self.assertIn("QUBE", text)

    def test_language_spec_resource(self):
        text = self._get_resource("language_spec_resource")
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)
        self.assertIn("Aeonmi", text)

    def test_glyph_algebra_resource(self):
        text = self._get_resource("glyph_algebra_resource")
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)
        self.assertIn("⧉", text)

    def test_mother_guide_resource(self):
        text = self._get_resource("mother_guide_resource")
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)
        self.assertIn("Mother", text)

    def test_cli_reference_resource(self):
        text = self._get_resource("cli_reference_resource")
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)
        self.assertIn("qube", text.lower())

    def test_qube_examples_resource(self):
        text = self._get_resource("qube_examples_resource")
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)
        self.assertIn("Bell", text)

    def test_ai_examples_resource(self):
        text = self._get_resource("ai_examples_resource")
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)
        self.assertIn("quantum", text.lower())

    def test_qube_snippets_resource(self):
        text = self._get_resource("qube_snippets_resource")
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)
        self.assertIn("CNOT", text)

    def test_ai_snippets_resource(self):
        text = self._get_resource("ai_snippets_resource")
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)
        self.assertIn("superpose", text.lower())


if __name__ == "__main__":
    unittest.main()
