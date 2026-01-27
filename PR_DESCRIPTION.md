# Feature: Interactive Debugging Mode

## Summary
Introduces a new interactive debugging mode for agent development. Developers can now pause execution, step through nodes, inspect memory state, and set breakpoints using a familiar CLI interface.

## Key Features
- **Interactive CLI**: `python -m framework.cli debug exports/my_agent`
- **Stepping**: `next` (n), `step` (s) to execute node-by-node.
- **Breakpoints**: `break <node_id>` to pause at specific nodes.
- **Inspection**: `memory` (m) to view agent state, `context` to view node inputs.
- **Mock Mode**: Support for `--mock` to run without real LLM calls (great for logic testing).

## Implementation Details
- **Debugger Module**: New `core/framework/debugger/` package with `DebugSession` and `DebugCLI`.
- **Executor Hooks**: Added `debug_hook` to `GraphExecutor` to intercept execution before each step.
- **Runner Integration**: Updated `AgentRunner` to support injecting debug hooks.
- **CLI Command**: Added `debug` subcommand to the main framework CLI.

## Usage
```bash
# Debug an agent
python -m framework debug exports/my_agent

# Debug with mock execution
python -m framework debug exports/my_agent --mock
```

## Example Session
```
(debug) next
▶ Step 1: Start (llm_generate)
   Running...
   ✓ Success
   → Next: Process

⏸  Paused at node: Process (node2)

(debug) memory
Memory Keys:
  greeting: "Hello world"

(debug) continue
```
