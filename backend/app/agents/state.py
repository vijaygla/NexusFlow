"""
NexusFlow State Definition
Defines the multi-agent graph execution state using LangGraph TypedDict.
Tracks dialogue, synthesized file trees, review evaluations, loop counter, active node,
and chronological iteration snapshots for the Iteration Time Machine & Diff Viewer.
"""

from typing import Annotated, Any, Dict, List, Optional, Sequence, Union
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class IterationSnapshot(TypedDict, total=False):
    """Snapshot of a single cycle in the cyclic agent workflow."""
    iteration: int
    files: Dict[str, str]
    review_feedback: str
    execution_result: Optional[Dict[str, Any]]
    node: str


class GraphState(TypedDict, total=False):
    """
    State container for the NexusFlow multi-agent cyclic workflow.

    Attributes:
        messages: Sequence of LangChain BaseMessage objects (human, AI, tool).
                  Merged using add_messages reducer.
        generated_code: Dictionary mapping file paths/names to code block contents.
        review_feedback: Validation notes and critique from the Reviewer Agent.
        iterations: Number of coder-reviewer loop cycles completed.
        current_node: Currently active agent node (e.g. 'coder', 'reviewer', 'complete').
        execution_result: Output captured by the code execution validation tool.
        iteration_history: Chronological list of snapshots for Diff / Time Machine inspection.
        language: Target programming language (e.g. 'python', 'javascript', 'typescript').
        error: Optional error string if validation or execution fails.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    generated_code: Dict[str, str]
    review_feedback: Union[str, List[str]]
    iterations: int
    current_node: str
    execution_result: Optional[Dict[str, Any]]
    iteration_history: List[Dict[str, Any]]
    language: str
    error: Optional[str]
