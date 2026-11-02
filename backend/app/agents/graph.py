"""
NexusFlow Cyclic Multi-Agent Graph Architecture
Compiles the LangGraph state machine orchestrating the Coder and Reviewer agents.
Utilizes MemorySaver checkpointer for stateful, multi-turn execution sessions.
"""

import logging
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.agents.state import GraphState
from app.agents.coder_agent import coder_node
from app.agents.reviewer_agent import reviewer_node
from app.config import get_settings

logger = logging.getLogger("nexusflow.graph")


def should_continue(state: GraphState) -> Literal["coder", "__end__"]:
    """
    Conditional routing function:
    Evaluates Reviewer Agent feedback and iteration limit.
    If defects or errors are found and iterations < 3, cycles back to Coder Agent.
    Otherwise, terminates the workflow and routes to END.
    """
    settings = get_settings()
    max_loops = settings.MAX_ITERATIONS
    iterations = state.get("iterations", 0)
    feedback = state.get("review_feedback", "")
    if isinstance(feedback, list):
        feedback = "\n".join(feedback)

    logger.info(f"[Router: should_continue] Evaluated loop {iterations}/{max_loops}.")

    # Termination check: Reached maximum allowed cyclic iterations
    if iterations >= max_loops:
        logger.info(f"[Router] Maximum iterations reached ({iterations}). Routing to END.")
        return END

    # Analyze Reviewer verdict
    upper_feedback = feedback.upper()
    needs_revision = "STATUS: NEEDS_REVISION" in upper_feedback or "NEEDS_REVISION" in upper_feedback
    has_passed = "STATUS: PASS" in upper_feedback

    if needs_revision and not has_passed:
        logger.info(f"[Router] Reviewer requested improvements. Routing back to Coder (next loop: {iterations + 1}).")
        return "coder"

    logger.info("[Router] Code satisfies quality standards or passed review. Routing to END.")
    return END


def create_nexus_graph() -> Any:
    """
    Builds and compiles the cyclic StateGraph with MemorySaver checkpointer.
    """
    workflow = StateGraph(GraphState)

    # 1. Register agent nodes
    workflow.add_node("coder", coder_node)
    workflow.add_node("reviewer", reviewer_node)

    # 2. Define workflow entry and sequential edges
    workflow.set_entry_point("coder")
    workflow.add_edge("coder", "reviewer")

    # 3. Define conditional cyclic edge from reviewer
    workflow.add_conditional_edges(
        "reviewer",
        should_continue,
        {
            "coder": "coder",
            END: END,
        },
    )

    # 4. Compile with stateful checkpointer
    checkpointer = MemorySaver()
    compiled_graph = workflow.compile(checkpointer=checkpointer)
    logger.info("Compiled NexusFlow multi-agent graph with MemorySaver checkpointer successfully.")
    return compiled_graph


# Pre-compiled singleton workflow graph
nexus_graph = create_nexus_graph()
