# Aeonmi Claude Connector

A **Model Context Protocol (MCP)** server that connects Claude to the
[Aeonmi / QUBE quantum programming language](https://github.com/Aeonmi-Aysa/aeonmi) —
a quantum-native language featuring a real statevector simulator, Unicode glyph algebra,
circle-function syntax, and the Mother AI REPL.

---

## What is Aeonmi / QUBE?

Aeonmi (`.ai`) is a quantum-aware programming language. QUBE (`.qube`) is its dedicated
quantum circuit description language. Together they support:

- **Real quantum gates** simulated with statevectors (H, X, Y, Z, S, T, CNOT, CZ, SWAP, Rx/Ry/Rz)
- **Qubit literals**: `|0⟩ |1⟩ |+⟩ |-⟩ |ψ⟩`
- **Unicode glyph algebra**: `⧉0.707‥0‥0‥0.707⧉`, `ψ ↦ bell ⊗ bell`
- **Circle-function syntax**: `◯ fn⟨params⟩ { }`, `⊙ quantum_fn⟨q⟩ { }`
- **Mother AI REPL**: self-evolving AI persona with bond system and genesis.json state

### QUBE quick reference

```
state q = |0⟩              declare qubit in |0⟩ state
state ψ = 0.707|0⟩ + 0.707|1⟩   equal superposition
apply H -> q               apply Hadamard gate
apply CNOT(q0, q1)         apply CNOT (entangle)
collapse q -> r            measure qubit → 0 or 1
assert r ∈ {0, 1}          check result
assert r == 1              exact check
log(r)                     print value
∴ comment                  line comment (therefore)
∵ reason                   line comment (because)
```

### Bell state example

```qube
∴ Bell state: maximally entangled pair
state q0 = |0⟩
state q1 = |0⟩
apply H -> q0
apply CNOT(q0, q1)
collapse q0 -> r0
collapse q1 -> r1
∵ Bell pair always collapses to the same bit
assert r0 ∈ {0, 1}
assert r1 ∈ {0, 1}
log(r0)
log(r1)
```

---

## Tools exposed to Claude

| Tool | Description |
|------|-------------|
| `qube_run_tool` | Execute a QUBE circuit → outputs, measurements, assertion failures, circuit steps |
| `qube_check_tool` | Parse-only validation → `{valid: true, statement_count: N}` |
| `qube_diagram_tool` | ASCII circuit diagram |
| `qube_explain_tool` | Explain a gate name, keyword, qubit literal, or comment glyph |
| `qube_generate_tool` | Generate QUBE code from plain English (bell, ghz, superposition, etc.) |
| `aeonmi_explain_tool` | Explain any `.ai` construct: glyphs, quantum ops, circle functions |
| `aeonmi_generate_tool` | Generate `.ai` code from plain English |
| `aeonmi_list_keywords_tool` | Full keyword/operator/glyph/builtin catalogue |
| `mother_help_tool` | Mother AI REPL command reference |
| `cli_help_tool` | `aeonmi` CLI subcommand reference |

## Resources exposed to Claude

| URI | Content |
|-----|---------|
| `aeonmi://docs/qube-grammar` | Full QUBE grammar reference |
| `aeonmi://docs/language-spec` | Aeonmi `.ai` language specification |
| `aeonmi://docs/glyph-algebra` | Glyph algebra primitives |
| `aeonmi://docs/mother-guide` | Mother AI overview and REPL commands |
| `aeonmi://docs/cli-reference` | CLI subcommand reference |
| `aeonmi://examples/qube` | Built-in QUBE example circuits |
| `aeonmi://examples/ai` | Built-in Aeonmi `.ai` example programs |
| `aeonmi://snippets/qube` | VS Code extension QUBE snippets guide |
| `aeonmi://snippets/ai` | VS Code extension Aeonmi snippets guide |

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

The server communicates over **stdio** using the standard MCP transport and works
with any MCP-compatible host (Claude Desktop, mcphost, etc.).

### Claude Desktop configuration

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "aeonmi": {
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

All 126 tests should pass.

---

## Project structure

```
src/aeonmi_claude_connector/
  qube_syntax.py    — token types, gate matrices, language references, examples
  qube_parser.py    — QUBE lexer and recursive-descent parser
  qube_executor.py  — real statevector quantum simulator
  server.py         — FastMCP server with all tools and resources
tests/
  test_qube_parser.py   — parser/tokenizer tests
  test_qube_executor.py — simulator tests
  test_server.py        — tool function tests
```

---

## Example: Claude using the tools

**Run a Bell state:**
```
You: Run this QUBE circuit for me:
  state q0 = |0⟩
  state q1 = |0⟩
  apply H -> q0
  apply CNOT(q0, q1)
  collapse q0 -> r0
  collapse q1 -> r1
  log(r0)
  log(r1)

Claude → qube_run_tool:
{
  "outputs": ["0", "0"],
  "measurements": {"r0": 0, "r1": 0},
  "assertion_failures": [],
  "circuit_steps": ["state q0 = |0⟩", "state q1 = |0⟩", ...]
}
```

**Generate a circuit:**
```
You: Generate QUBE code for a GHZ state.

Claude → qube_generate_tool("ghz state"):
{
  "code": "∴ GHZ state: three-qubit entanglement\nstate a = |0⟩\n...",
  "description": "GHZ state: three-qubit Greenberger-Horne-Zeilinger entangled state."
}
```

---

## License

MIT
