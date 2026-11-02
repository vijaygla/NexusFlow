"""
NexusFlow Universal Multi-Language Reviewer Agent Node
Conducts deep static, semantic, and architectural code reviews across ANY programming language.
Evaluates execution telemetry and assigns PASS or NEEDS_REVISION status.
"""

import logging
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.agents.state import GraphState
from app.agents.llm import get_chat_model
from app.config import get_settings

logger = logging.getLogger("nexusflow.reviewer")


def build_reviewer_system_prompt(language: str) -> str:
    lang_upper = language.upper()
    return f"""You are the Principal Code Reviewer and Lead Security Architect at NexusFlow.
Your responsibility is to strictly audit all code synthesized in {lang_upper} by the Coder Agent.

REVIEW CRITERIA ({lang_upper}):
1. FUNCTIONAL CORRECTNESS & LOGIC:
   - Does the implementation fully solve the user's requirements?
   - Are there hidden edge-case bugs, off-by-one errors, or improper exception/error handling in {lang_upper}?
2. EXECUTION & TEST TELEMETRY:
   - Did the automated test/validation suite pass (exit code 0)?
   - If execution failed or timed out, you MUST issue STATUS: NEEDS_REVISION and detail the exact failure trace.
3. LANGUAGE IDIOMS & BEST PRACTICES:
   - Does the code follow idiomatic {lang_upper} conventions, naming standards, and architectural patterns?
   - Are types, memory safety, and resource management properly handled?

MANDATORY OUTPUT FORMAT:
You MUST conclude your review with an explicit status line:

If all code is sound, tests passed, and no critical defects remain:
STATUS: PASS

If bugs, failing tests, or significant improvements are required:
STATUS: NEEDS_REVISION

Structure your report clearly:
- Summary of Findings ({lang_upper})
- Test & Execution Assessment
- Identified Defects / Edge Cases
- Actionable Recommendations for Coder Agent
- STATUS: PASS or STATUS: NEEDS_REVISION
"""


async def reviewer_node(state: GraphState) -> Dict[str, Any]:
    """
    Reviewer Node execution:
    1. Inspects state generated_code and execution_result in target language.
    2. Runs LLM audit against architectural and functional standards for that language.
    3. Updates state with review_feedback and current_node.
    """
    settings = get_settings()
    llm = get_chat_model(model_name=settings.REVIEWER_MODEL, temperature=0.1)

    generated_code = state.get("generated_code", {})
    execution_result = state.get("execution_result", {})
    iterations = state.get("iterations", 1)
    target_language = state.get("language", "python")

    # Format files for the reviewer prompt
    code_sections = []
    for fname, code in generated_code.items():
        code_sections.append(f"### FILE: {fname}\n```{target_language}\n{code}\n```")
    all_code_str = "\n\n".join(code_sections) if code_sections else "(No code generated)"

    exec_status = "SUCCESS" if execution_result.get("success") else "FAILED"
    telemetry_str = (
        f"Target Language: {target_language.upper()}\n"
        f"Execution Outcome: {exec_status}\n"
        f"Exit Code: {execution_result.get('exit_code')}\n"
        f"Stdout:\n{execution_result.get('stdout', '')}\n"
        f"Stderr/Traceback:\n{execution_result.get('stderr', '')}"
    )

    review_input = (
        f"CODE REVIEW AUDIT (ITERATION {iterations} - {target_language.upper()})\n\n"
        f"SYNTHESIZED CODEBASE:\n{all_code_str}\n\n"
        f"AUTOMATED VALIDATION TELEMETRY:\n{telemetry_str}\n\n"
        f"Please provide your rigorous architectural code review in {target_language.upper()} and conclude with STATUS: PASS or STATUS: NEEDS_REVISION."
    )

    system_prompt = build_reviewer_system_prompt(target_language)
    messages: List[Any] = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=review_input),
    ]

    logger.info(f"[Reviewer Node] Reviewing {target_language.upper()} code for iteration {iterations}...")
    ai_response = await llm.ainvoke(messages)
    review_text = ai_response.content if isinstance(ai_response.content, str) else str(ai_response.content)

    return {
        "review_feedback": review_text,
        "current_node": "reviewer",
        "messages": [AIMessage(content=f"### Reviewer Agent Audit (Iteration {iterations} - {target_language.upper()}):\n\n{review_text}")],
    }
