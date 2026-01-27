import cmd
import json
import logging
import sys
from typing import Any, Dict, List, Set, Optional

from framework.graph.executor import GraphExecutor, ExecutionResult
from framework.graph.node import NodeSpec
from framework.graph.goal import Goal
from framework.graph.edge import GraphSpec

class DebugSession:
    """
    Manages a debugging session for an agent execution.
    
    Controls execution flow:
    - Step-by-step execution
    - Breakpoints
    - State inspection
    """
    
    def __init__(self, executor: GraphExecutor):
        self.executor = executor
        self.breakpoints: Set[str] = set()  # Node IDs to break on
        self.pause_on_next: bool = True     # Start paused
        self.history: List[Dict[str, Any]] = [] # Execution history
        self.current_step_info: Optional[Dict[str, Any]] = None
        
        # Hook into the executor
        # We need to modify Executor to accept a debug hook, 
        # or subclass it. For now, we'll assume we can pass a callback.
        if hasattr(executor, 'set_debug_hook'):
            executor.set_debug_hook(self.on_step)
        
    def add_breakpoint(self, node_id: str):
        """Add a breakpoint at specific node."""
        self.breakpoints.add(node_id)
        print(f"Breakpoint set at '{node_id}'")

    def remove_breakpoint(self, node_id: str):
        """Remove a breakpoint."""
        if node_id in self.breakpoints:
            self.breakpoints.remove(node_id)
            print(f"Breakpoint removing from '{node_id}'")
        else:
            print(f"No breakpoint found at '{node_id}'")

    def list_breakpoints(self):
        """List all breakpoints."""
        if not self.breakpoints:
            print("No breakpoints set.")
        else:
            print("Breakpoints:")
            for bp in self.breakpoints:
                print(f"  - {bp}")

    def on_step(self, node_id: str, node_spec: NodeSpec, context: Dict[str, Any], memory: Dict[str, Any]) -> str:
        """
        Callback triggered before each node execution.
        
        Returns command: 'continue', 'step', 'quit' or modified state.
        """
        should_break = (
            self.pause_on_next or 
            node_id in self.breakpoints
        )
        
        self.current_step_info = {
            "node_id": node_id,
            "node_name": node_spec.name,
            "inputs": context,
            "memory": memory
        }
        
        if should_break:
            self.pause_on_next = False # Reset single step
            return "break"
        
        return "continue"

    def resume(self):
        """Continue execution until next breakpoint."""
        self.pause_on_next = False

    def step(self):
        """Execute next step and pause."""
        self.pause_on_next = True

    def get_memory_snapshot(self) -> Dict[str, Any]:
        """Get current memory state."""
        return self.current_step_info.get("memory", {}) if self.current_step_info else {}

    def get_context(self) -> Dict[str, Any]:
        """Get current inputs/context."""
        return self.current_step_info.get("inputs", {}) if self.current_step_info else {}
