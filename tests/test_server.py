"""Tests for the MCP server tools."""

import json

import pytest

from aeonmi_claude_connector.server import call_tool, list_tools, list_resources, read_resource


# ---------------------------------------------------------------------------
# Tools list
# ---------------------------------------------------------------------------

class TestListTools:
    @pytest.mark.asyncio
    async def test_returns_expected_tools(self):
        tools = await list_tools()
        names = {t.name for t in tools}
        assert names == {
            "qube_parse",
            "qube_execute",
            "qube_validate",
            "qube_explain",
            "qube_generate",
            "qube_list_glyphs",
        }

    @pytest.mark.asyncio
    async def test_each_tool_has_schema(self):
        tools = await list_tools()
        for tool in tools:
            assert tool.inputSchema is not None


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

class TestResources:
    @pytest.mark.asyncio
    async def test_list_resources(self):
        resources = await list_resources()
        uris = {str(r.uri) for r in resources}
        assert "qube://syntax/glyphs" in uris
        assert "qube://syntax/grammar" in uris
        assert "qube://examples" in uris

    @pytest.mark.asyncio
    async def test_read_glyphs_resource(self):
        content = await read_resource("qube://syntax/glyphs")
        data = json.loads(content)
        assert "λ" in data
        assert "⊗" in data

    @pytest.mark.asyncio
    async def test_read_grammar_resource(self):
        content = await read_resource("qube://syntax/grammar")
        assert "QUBE Grammar" in content
        assert "binding" in content

    @pytest.mark.asyncio
    async def test_read_examples_resource(self):
        content = await read_resource("qube://examples")
        data = json.loads(content)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "code" in data[0]

    @pytest.mark.asyncio
    async def test_unknown_resource_raises(self):
        with pytest.raises(ValueError):
            await read_resource("qube://unknown")


# ---------------------------------------------------------------------------
# qube_parse tool
# ---------------------------------------------------------------------------

class TestQubeParseTool:
    @pytest.mark.asyncio
    async def test_parse_returns_ast(self):
        result = await call_tool("qube_parse", {"source": "λ x ≔ ∞"})
        data = json.loads(result[0].text)
        assert data["_type"] == "Program"
        assert len(data["statements"]) == 1

    @pytest.mark.asyncio
    async def test_parse_error_returns_error_key(self):
        result = await call_tool("qube_parse", {"source": "λ x |bad"})
        data = json.loads(result[0].text)
        assert "error" in data


# ---------------------------------------------------------------------------
# qube_execute tool
# ---------------------------------------------------------------------------

class TestQubeExecuteTool:
    @pytest.mark.asyncio
    async def test_execute_root_soul(self):
        result = await call_tool("qube_execute", {"source": "λ RootSoul ≔ |ψ⟩ ⊗ ∞"})
        data = json.loads(result[0].text)
        assert "RootSoul" in data["bindings"]

    @pytest.mark.asyncio
    async def test_execute_with_seed(self):
        args = {"source": '↯ (|"yes"⟩ ⊕ |"no"⟩)', "seed": 42}
        r1 = await call_tool("qube_execute", args)
        r2 = await call_tool("qube_execute", args)
        assert r1[0].text == r2[0].text

    @pytest.mark.asyncio
    async def test_execute_returns_entropy(self):
        result = await call_tool("qube_execute", {"source": "⧖ 7"})
        data = json.loads(result[0].text)
        assert data["entropy_credits"] == pytest.approx(7.0)

    @pytest.mark.asyncio
    async def test_execute_parse_error(self):
        result = await call_tool("qube_execute", {"source": "λ x |bad"})
        data = json.loads(result[0].text)
        assert "error" in data


# ---------------------------------------------------------------------------
# qube_validate tool
# ---------------------------------------------------------------------------

class TestQubeValidateTool:
    @pytest.mark.asyncio
    async def test_valid_source(self):
        result = await call_tool("qube_validate", {"source": "λ x ≔ ∞"})
        data = json.loads(result[0].text)
        assert data["valid"] is True

    @pytest.mark.asyncio
    async def test_invalid_source(self):
        result = await call_tool("qube_validate", {"source": "λ x |bad"})
        data = json.loads(result[0].text)
        assert data["valid"] is False
        assert "error" in data


# ---------------------------------------------------------------------------
# qube_explain tool
# ---------------------------------------------------------------------------

class TestQubeExplainTool:
    @pytest.mark.asyncio
    async def test_explain_single_glyph(self):
        result = await call_tool("qube_explain", {"input": "⊗"})
        assert "entanglement" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_explain_lambda(self):
        result = await call_tool("qube_explain", {"input": "λ"})
        assert "flow" in result[0].text.lower() or "function" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_explain_expression(self):
        result = await call_tool("qube_explain", {"input": "λ x ≔ |ψ⟩ ⊗ ∞"})
        text = result[0].text
        assert "λ" in text or "⊗" in text

    @pytest.mark.asyncio
    async def test_explain_no_glyphs(self):
        result = await call_tool("qube_explain", {"input": "hello world"})
        assert "No QUBE glyphs" in result[0].text


# ---------------------------------------------------------------------------
# qube_generate tool
# ---------------------------------------------------------------------------

class TestQubeGenerateTool:
    @pytest.mark.asyncio
    async def test_generate_entangle(self):
        result = await call_tool("qube_generate", {"description": "entangle two states"})
        assert "⊗" in result[0].text

    @pytest.mark.asyncio
    async def test_generate_superpose(self):
        result = await call_tool("qube_generate", {"description": "superpose two outcomes"})
        assert "⊕" in result[0].text

    @pytest.mark.asyncio
    async def test_generate_collapse(self):
        result = await call_tool("qube_generate", {"description": "collapse a measurement"})
        assert "↯" in result[0].text

    @pytest.mark.asyncio
    async def test_generate_lock(self):
        result = await call_tool("qube_generate", {"description": "lock and secure a node"})
        assert "◈" in result[0].text

    @pytest.mark.asyncio
    async def test_generate_fallback(self):
        # Unrecognised description should still produce valid QUBE
        result = await call_tool("qube_generate", {"description": "xyzzy magic"})
        text = result[0].text
        assert "λ" in text

    @pytest.mark.asyncio
    async def test_generated_code_is_valid(self):
        """Generated code should parse without errors."""
        result = await call_tool("qube_generate", {"description": "entangle two states"})
        # Extract the code block
        text = result[0].text
        code_block = text.split("```")[1].strip() if "```" in text else text
        validate_result = await call_tool("qube_validate", {"source": code_block})
        data = json.loads(validate_result[0].text)
        assert data["valid"] is True


# ---------------------------------------------------------------------------
# qube_list_glyphs tool
# ---------------------------------------------------------------------------

class TestQubeListGlyphsTool:
    @pytest.mark.asyncio
    async def test_returns_table(self):
        result = await call_tool("qube_list_glyphs", {})
        text = result[0].text
        assert "λ" in text
        assert "⊗" in text
        assert "∞" in text

    @pytest.mark.asyncio
    async def test_all_glyphs_present(self):
        from aeonmi_claude_connector.qube_syntax import GLYPHS
        result = await call_tool("qube_list_glyphs", {})
        text = result[0].text
        for glyph in GLYPHS:
            assert glyph in text, f"Glyph {glyph!r} missing from list"


# ---------------------------------------------------------------------------
# Unknown tool
# ---------------------------------------------------------------------------

class TestUnknownTool:
    @pytest.mark.asyncio
    async def test_unknown_tool_raises(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            await call_tool("nonexistent_tool", {})
