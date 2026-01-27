# 🐝 Aden Agent Framework - Comprehensive Project Guide

This document provides a detailed technical overview of the Aden Agent Framework. It is designed to help new developers understand the architecture, key components, and data flow of the system.

---

## 1. High-Level Architecture

The framework is designed to build **Graph-Based Agents**. Unlike linear chains (Step A -> Step B), graph agents can loop, branch, and adapt based on outcomes.

### Core Concepts

*   **Agent**: A collection of Nodes and Edges designed to achieve a specific Goal.
*   **Graph**: The directed graph structure defining the agent's logic.
*   **Node**: A unit of work (e.g., "Generate Text", "Execute Code", "Search Web").
*   **Edge**: Examples the rules for moving from one node to another (e.g., "If score > 0.8, go to Finish").
*   **Memory**: Shared state accessible by all nodes during execution.
*   **Runtime**: The engine that executes the graph, manages state, and handles I/O.

---

## 2. Directory Structure & Key Files

The codebase is organized into three main areas: `core` (framework logic), `tools` (capabilities), and `exports` (saved agents).

### 🧠 `core/framework` - The Brain

This is where the magic happens.

#### `graph/` - The Blueprint
*   **`node.py`**: Defines `Node` and `NodeProtocol`. This is the base class for all steps.
*   **`edge.py`**: Defines `Edge` and `EdgeCondition`. Handles logic like `ON_SUCCESS`, `ON_FAILURE`, or `CONDITIONAL` (LLM-decided).
*   **`executor.py`** & **`graph_executor.py`**: The "Game Loop". It looks at the current node, executes it, checks edges, and decides the next node.
*   **`goal.py`**: Defines `Goal`, `SuccessCriterion`, and `Constraint`. This ensures the agent isn't just running blindly but trying to achieve specific metrics.

#### `runner/` - The Control Center
*   **`runner.py`**: The main entry point for *loading* and *running* an agent. It instantiates the `Runtime`, sets up tools, and kicks off the `Executor`.
*   **`cli.py`**: The command-line interface. Handles commands like `run`, `list`, and the new `debug`.
*   **`tool_registry.py`**: Manages available tools and hands them to the agent.

#### `llm/` - The Voice
*   **`provider.py`**: Abstract base class for LLMs.
*   **`litellm.py`**: Integration with the `litellm` library to support 100+ models (OpenAI, Anthropic, Gemini, etc.) using a unified API.

#### `runtime/` - The State Manager
*   **`core.py`**: Manages the "Session". Keeps track of the execution history, logs, and shared memory.
*   **`storage/`**: Handles saving/loading state to disk or database.

#### `debugger/` - (New Feature)
*   **`session.py`**: Manages debug state (paused/running, breakpoints).
*   **`cli_interface.py`**: The interactive `(debug)` prompt logic.

### 🛠️ `tools/` - The Capabilities

Agents are useless without tools. This folder contains:
*   **`src/aden_tools/tools/`**: Actual Python implementations of tools.
    *   `web_search_tool/`: **Multi-provider search** (Google & Brave). Handles rate limits and auth.
    *   `web_scrape_tool/`: Reading website content.
    *   `file_system_toolkits/`: Reading/Writing files.
*   **`mcp_server.py`**: Implementation of the **Model Context Protocol (MCP)**. This allows these tools to be served as an API that any MCP-compliant LLM (like Claude) can use.

### � `exports/` - The Agents

When you build an agent (using the no-code builder or manually), it gets saved here.
*   **`my_agent/agent.json`**: The JSON file defining the Nodes, Edges, and Goal.
*   **`my_agent/tools.py`**: (Optional) Custom Python tools specific to this agent.

---

## 3. Data Flow: How an Agent Runs

When you run `python -m framework run exports/research_agent`:

1.  **Load**: `AgentRunner.load()` reads `agent.json`. It builds the `GraphSpec` object.
2.  **Setup**:
    *   It detects `tools.py` and registers functions.
    *   It initializes the LLM provider (e.g., GPT-4).
    *   It creates a `Runtime` to store memory.
3.  **Execute (The Loop)**:
    *   **Start**: The `Executor` looks at the `entry_node`.
    *   **Pre-Step**: (New) Checks for `debug_hook`. If a breakpoint exists, it pauses and waits for user input.
    *   **Run Node**: The Node executes (e.g., calls LLM).
    *   **Update Memory**: The output of the node is saved to shared memory.
    *   **Decide Next**: The `Executor` evaluates all `edges` connected to the current node.
        *   *Example*: If "Research" node output is "Found nothing", the "Conditional" edge might point back to "Modify Search Query".
    *   **Repeat**: This continues until a `terminal_node` is reached or `max_steps` is exceeded.

---

## 4. Key Technical Decisions

*   **Node-Based**: Everything is a node. This makes the system modular. You can swap out the "Search" node for a "Mock Search" node easily.
*   **Shared Memory**: Nodes communicate via a shared dictionary (`context`). Node A writes to `context["query"]`, Node B reads from `context["query"]`.
*   **Pydantic**: We use Pydantic models for strict type validation where possible (though validation of LLM outputs is a Work In Progress).
*   **MCP First**: The system is designed to be compatible with the Model Context Protocol, making it future-proof for the Agentic ecosystem.

---

## 5. Current Challenges & Roadmap

### 🔴 Immediate Problems
*   **Output Consistency**: LLMs sometimes output invalid JSON. We need **Pydantic Validation** layers (In Roadmap).
*   **Observability**: It's hard to see *why* an agent failed. The **Debugger** (just added) helps, but visual tracing would be better.
*   **Tooling**: The Web Scraper is basic. It needs to handle JS-heavy sites (headless browser support).

### 🟡 Tech Debt
*   **Validation**: The `agent.json` schema is loose. We need stricter validation to ensure imported agents are valid before running.
*   **Testing**: We need more unit tests for individual nodes, not just full integration tests.

### 🟢 Next Steps (Roadmap)
1.  **Pydantic Validation**: Enforce strict output schemas from LLMs.
2.  **Web Scraper**: Improve the scraping tool.
3.  **LLM Streaming** (✅ JUST ADDED): Real-time token delivery support for better UX and monitoring.
4.  **Sample Agents**: Build "Standard Library" agents (e.g., Coder, Writer, Researcher) to show off the framework.
