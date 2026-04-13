"""Aeonmi Claude Connector — MCP server.

Exposes the following tools to Claude:
  • qube_parse       — parse QUBE source and return the AST as JSON
  • qube_execute     — execute a QUBE workflow and return the result
  • qube_validate    — validate QUBE syntax and report errors
  • qube_explain     — explain a QUBE glyph or expression in plain English
  • qube_generate    — generate QUBE code from a plain-English description
  • qube_list_glyphs — list all QUBE glyphs with descriptions

And the following resources:
  • qube://syntax/glyphs   — full glyph catalogue
  • qube://syntax/grammar  — grammar reference
  • qube://examples        — built-in example programs
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server
from mcp.server.models import InitializationOptions

from .qube_executor import execute as qube_execute_source
from .qube_parser import ParseError, parse as qube_parse_source
from .qube_syntax import EXAMPLES, GLYPHS, GRAMMAR_REFERENCE

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ast_to_dict(node: Any) -> Any:
    """Recursively convert an AST node into a JSON-serialisable dict."""
    if node is None:
        return None
    if isinstance(node, (int, float, str, bool)):
        return node
    if isinstance(node, list):
        return [_ast_to_dict(item) for item in node]
    # dataclass
    try:
        d = asdict(node)  # type: ignore[call-overload]
        d["_type"] = type(node).__name__
        return d
    except TypeError:
        return str(node)


# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------

app = Server("aeonmi-claude-connector")


# ---- Resources -------------------------------------------------------------

@app.list_resources()
async def list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri="qube://syntax/glyphs",
            name="QUBE Glyph Catalogue",
            description="All QUBE glyphs with their meanings.",
            mimeType="application/json",
        ),
        types.Resource(
            uri="qube://syntax/grammar",
            name="QUBE Grammar Reference",
            description="Formal grammar for the QUBE quantum syntax.",
            mimeType="text/plain",
        ),
        types.Resource(
            uri="qube://examples",
            name="QUBE Example Programs",
            description="Built-in example QUBE workflows.",
            mimeType="application/json",
        ),
    ]


@app.read_resource()
async def read_resource(uri: types.AnyUrl) -> str:
    uri_str = str(uri)
    if uri_str == "qube://syntax/glyphs":
        return json.dumps(GLYPHS, ensure_ascii=False, indent=2)
    if uri_str == "qube://syntax/grammar":
        return GRAMMAR_REFERENCE
    if uri_str == "qube://examples":
        return json.dumps(EXAMPLES, ensure_ascii=False, indent=2)
    raise ValueError(f"Unknown resource URI: {uri_str}")


# ---- Tools -----------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="qube_parse",
            description=(
                "Parse a QUBE source string and return the Abstract Syntax Tree "
                "(AST) as a JSON object. Useful for inspecting the structure of a "
                "QUBE program before executing it."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "QUBE source code to parse.",
                    }
                },
                "required": ["source"],
            },
        ),
        types.Tool(
            name="qube_execute",
            description=(
                "Execute a QUBE workflow and return the runtime result, including "
                "all named bindings, any collapsed (measured) values, top-level "
                "expression outputs, and the current entropy-credit balance."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "QUBE source code to execute.",
                    },
                    "seed": {
                        "type": "integer",
                        "description": (
                            "Optional random seed for deterministic quantum collapse. "
                            "Omit for non-deterministic (true quantum) behaviour."
                        ),
                    },
                },
                "required": ["source"],
            },
        ),
        types.Tool(
            name="qube_validate",
            description=(
                "Validate QUBE syntax and return a structured report. "
                "Returns {valid: true} on success, or {valid: false, error: '...'} "
                "with a human-readable description of the parse error."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "QUBE source code to validate.",
                    }
                },
                "required": ["source"],
            },
        ),
        types.Tool(
            name="qube_explain",
            description=(
                "Explain a QUBE glyph or a short QUBE expression in plain English. "
                "Pass a single glyph character (e.g. '⊗') to get its definition, "
                "or pass a full expression (e.g. 'λ x ≔ |ψ⟩ ⊗ ∞') for a "
                "step-by-step breakdown."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": "A QUBE glyph or expression to explain.",
                    }
                },
                "required": ["input"],
            },
        ),
        types.Tool(
            name="qube_generate",
            description=(
                "Generate QUBE syntax from a plain-English description of the "
                "desired workflow. Returns ready-to-execute QUBE code and a "
                "brief explanation of each generated statement."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": (
                            "Plain-English description of the QUBE workflow to generate."
                        ),
                    }
                },
                "required": ["description"],
            },
        ),
        types.Tool(
            name="qube_list_glyphs",
            description="Return the complete QUBE glyph catalogue as a formatted table.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]


@app.call_tool()
async def call_tool(
    name: str,
    arguments: dict[str, Any],
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:

    # ---- qube_parse --------------------------------------------------------
    if name == "qube_parse":
        source = arguments["source"]
        try:
            ast = qube_parse_source(source)
            result = json.dumps(_ast_to_dict(ast), ensure_ascii=False, indent=2)
            return [types.TextContent(type="text", text=result)]
        except (SyntaxError, ParseError) as exc:
            error = {"error": str(exc)}
            return [types.TextContent(type="text", text=json.dumps(error))]

    # ---- qube_execute ------------------------------------------------------
    if name == "qube_execute":
        source = arguments["source"]
        seed = arguments.get("seed")
        try:
            result = qube_execute_source(source, seed=seed)
            return [types.TextContent(
                type="text",
                text=json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            )]
        except (SyntaxError, ParseError) as exc:
            error = {"error": f"Parse error: {exc}"}
            return [types.TextContent(type="text", text=json.dumps(error))]
        except Exception as exc:  # noqa: BLE001
            error = {"error": f"Runtime error: {exc}"}
            return [types.TextContent(type="text", text=json.dumps(error))]

    # ---- qube_validate -----------------------------------------------------
    if name == "qube_validate":
        source = arguments["source"]
        try:
            qube_parse_source(source)
            return [types.TextContent(type="text", text=json.dumps({"valid": True}))]
        except (SyntaxError, ParseError) as exc:
            return [types.TextContent(
                type="text",
                text=json.dumps({"valid": False, "error": str(exc)}),
            )]

    # ---- qube_explain ------------------------------------------------------
    if name == "qube_explain":
        user_input = arguments["input"].strip()

        # Single glyph lookup
        if user_input in GLYPHS:
            definition = GLYPHS[user_input]
            text = f"**{user_input}** — {definition}"
            return [types.TextContent(type="text", text=text)]

        # Multi-glyph: explain each glyph found
        lines: list[str] = [f"Explanation of: `{user_input}`", ""]
        found_any = False
        for glyph, desc in GLYPHS.items():
            if glyph in user_input:
                lines.append(f"  **{glyph}** — {desc}")
                found_any = True

        if not found_any:
            lines.append("No QUBE glyphs were found in the input.")
        else:
            # Also try to parse and describe the structure
            try:
                ast = qube_parse_source(user_input)
                stmt_types = [type(s).__name__ for s in ast.statements]
                lines.append("")
                lines.append(f"Parsed structure: {', '.join(stmt_types)}")
            except (SyntaxError, ParseError):
                pass

        return [types.TextContent(type="text", text="\n".join(lines))]

    # ---- qube_generate -----------------------------------------------------
    if name == "qube_generate":
        description = arguments["description"].lower()
        lines: list[str] = []
        explanations: list[str] = []

        # Keyword-driven template generation
        if any(w in description for w in ("bind", "assign", "define", "name", "call")):
            lines.append("λ myFlow ≔ |ψ⟩")
            explanations.append("λ myFlow ≔ |ψ⟩  — binds 'myFlow' to a generic quantum state")

        if any(w in description for w in ("entangle", "tensor", "link", "connect", "pair")):
            lines.append("λ pair ≔ |A⟩ ⊗ |B⟩")
            explanations.append("λ pair ≔ |A⟩ ⊗ |B⟩  — entangles states A and B")

        if any(w in description for w in ("superpose", "merge", "combine", "either", "or")):
            lines.append('λ choice ≔ |"yes"⟩ ⊕ |"no"⟩')
            explanations.append('λ choice ≔ |"yes"⟩ ⊕ |"no"⟩  — superpose two outcomes')

        if any(w in description for w in ("collapse", "measure", "observe", "classical")):
            lines.append("↯ choice")
            explanations.append("↯ choice  — collapse the superposition to one classical value")

        if any(w in description for w in ("loop", "evolve", "iterate", "self", "recurse")):
            lines.append("λ loop ≔ ⟳ |ψ⟩")
            explanations.append("λ loop ≔ ⟳ |ψ⟩  — create a self-evolving state")

        if any(w in description for w in ("lock", "secure", "immutable", "glyph-lock", "seal")):
            lines.append("λ sealed ≔ ◈ Æ(∞)")
            explanations.append("λ sealed ≔ ◈ Æ(∞)  — create a glyph-locked constructor node")

        if any(w in description for w in ("entropy", "credit", "budget", "resource")):
            lines.append("λ budget ≔ ⧖ 100")
            explanations.append("λ budget ≔ ⧖ 100  — allocate 100 entropy credits")

        if any(w in description for w in ("flow", "pipe", "chain", "stream", "send")):
            lines.append("λ pipeline ≔ |ψ⟩ ↝ ⟳ |ψ⟩")
            explanations.append("λ pipeline ≔ |ψ⟩ ↝ ⟳ |ψ⟩  — pipe a state into a self-evolving loop")

        if any(w in description for w in ("constructor", "ai", "node", "brain", "memory")):
            lines.append("λ brain ≔ Æ(∞)")
            explanations.append("λ brain ≔ Æ(∞)  — instantiate an Aeonmi Constructor AI node")

        if any(w in description for w in ("infinite", "∞", "unbounded", "eternal", "forever")):
            lines.append("λ storage ≔ Æ(∞) ⊗ ∞")
            explanations.append("λ storage ≔ Æ(∞) ⊗ ∞  — constructor entangled with infinite storage")

        # Fallback
        if not lines:
            lines.append("λ flow ≔ |ψ⟩ ⊗ ∞")
            explanations.append("λ flow ≔ |ψ⟩ ⊗ ∞  — default: a quantum state entangled with infinity")

        code = "\n".join(lines)
        explanation_text = "\n".join(f"  {e}" for e in explanations)
        output = f"Generated QUBE code:\n\n```\n{code}\n```\n\nStatement breakdown:\n{explanation_text}"
        return [types.TextContent(type="text", text=output)]

    # ---- qube_list_glyphs --------------------------------------------------
    if name == "qube_list_glyphs":
        max_glyph_len = max(len(g) for g in GLYPHS)
        header = f"{'Glyph':<{max_glyph_len + 2}}  Description"
        separator = "-" * len(header)
        rows = [f"{g:<{max_glyph_len + 2}}  {desc}" for g, desc in GLYPHS.items()]
        table = "\n".join([header, separator] + rows)
        return [types.TextContent(type="text", text=table)]

    raise ValueError(f"Unknown tool: {name!r}")


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the MCP server over stdio (standard MCP transport)."""
    import asyncio

    async def _run() -> None:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="aeonmi-claude-connector",
                    server_version="0.1.0",
                    capabilities=app.get_capabilities(
                        notification_options=None,
                        experimental_capabilities={},
                    ),
                ),
            )

    asyncio.run(_run())
