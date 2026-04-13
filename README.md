# Aeonmi Claude Connector

A **Model Context Protocol (MCP)** server that connects Claude to the
[Aeonmi / QUBE quantum syntax](https://github.com/DarthMetaCrypro/Aeonmi-Quantum-Workflow) —
a glyph-locked, quantum-inspired automation language featuring Constructor AI,
holographic storage, and self-evolving flows.

---

## What is QUBE?

QUBE is the pure Æ + Q.U.B.E. syntax at the heart of the Aeonmi Quantum Workflow.
It uses Unicode glyphs to express quantum-inspired operations:

| Glyph | Meaning |
|-------|---------|
| `λ`  | flow / function definition |
| `≔`  | assignment / binding |
| `⊗`  | entanglement (tensor product) |
| `⊕`  | superposition |
| `↯`  | collapse / measure |
| `⟳`  | self-evolve |
| `◈`  | glyph-lock (immutable / sealed) |
| `↝`  | flow-to pipe |
| `∞`  | infinity / holographic storage |
| `Æ`  | Aeonmi Constructor AI node |
| `⧖`  | entropy credit |
| `\|…⟩` | quantum state literal (Dirac ket) |

**Canonical hello-world:**
```
λ RootSoul ≔ |ψ⟩ ⊗ ∞
```

---

## Tools exposed to Claude

| Tool | Description |
|------|-------------|
| `qube_parse` | Parse QUBE source → JSON AST |
| `qube_execute` | Execute a QUBE workflow → runtime result |
| `qube_validate` | Validate QUBE syntax |
| `qube_explain` | Explain a glyph or expression |
| `qube_generate` | Generate QUBE code from plain English |
| `qube_list_glyphs` | List all glyphs with descriptions |

## Resources exposed to Claude

| URI | Content |
|-----|---------|
| `qube://syntax/glyphs` | Full glyph catalogue (JSON) |
| `qube://syntax/grammar` | Formal grammar reference |
| `qube://examples` | Built-in example programs (JSON) |

---

## Installation

```bash
pip install .
```

Or in development mode:

```bash
pip install -e ".[dev]"
```

---

## Running the server

```bash
# via the installed script
aeonmi-connector

# or as a module
python -m aeonmi_claude_connector
```

The server communicates over **stdio** using the standard MCP transport, so it
works with any MCP-compatible host (Claude Desktop, mcphost, etc.).

### Claude Desktop configuration

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "aeonmi-qube": {
      "command": "aeonmi-connector"
    }
  }
}
```

---

## Testing

```bash
pytest
```

All 92 tests should pass.

---

## Example session

```
You: Execute this QUBE workflow: λ greeting ≔ |"Hello"⟩ ⊕ |"Aysa"⟩

Claude (via qube_execute):
{
  "bindings": { "greeting": "(|Hello⟩@0.500 ⊕ |Aysa⟩@0.500)" },
  "entropy_credits": 0.0,
  "collapsed_values": [],
  "outputs": []
}

You: Now collapse it.

Claude (via qube_execute):
↯ greeting   →   collapsed_values: ["'Hello'"]
```

---

## License

MIT
