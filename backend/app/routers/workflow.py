"""
NexusFlow Real-Time Streaming & Execution Router
Exposes asynchronous Server-Sent Events (SSE) stream endpoint, synchronous execution endpoints,
multi-language sandbox runner, static security auditor, and MS SQL Server session history endpoints.
"""

import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from app.schemas.chat import ChatRequest, ChatResponse, StreamEventPayload, ExecutionOutput
from app.agents.graph import nexus_graph
from app.agents.state import GraphState
from app.tools.code_executor import run_code_validation
from app.tools.security_scanner import audit_codebase_security, audit_code_security
from app.db import (
    log_execution,
    get_execution_history,
    get_execution_by_session_id,
    get_analytics_metrics,
)

logger = logging.getLogger("nexusflow.workflow")
router = APIRouter(prefix="/api/workflow", tags=["Workflow"])


def format_sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """Formats payload as standard Server-Sent Event data line."""
    payload = {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **data,
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def generate_workflow_events(request: ChatRequest) -> AsyncGenerator[str, None]:
    """
    Asynchronous event generator executing the LangGraph workflow
    and streaming SSE events: node transitions, raw token chunks, code updates,
    iteration snapshots for the Time Machine, and final status.
    """
    session_id = request.session_id or str(uuid.uuid4())
    logger.info(f"[Workflow Stream] Starting session: {session_id} for prompt: {request.prompt[:80]}...")

    initial_state: GraphState = {
        "messages": [HumanMessage(content=request.prompt)],
        "generated_code": {},
        "review_feedback": "",
        "iterations": 0,
        "current_node": "init",
        "execution_result": None,
        "iteration_history": [],
        "language": request.language or "python",
    }

    config = {
        "configurable": {
            "thread_id": session_id,
        }
    }

    yield format_sse_event(
        "start",
        {
            "session_id": session_id,
            "node": "init",
            "prompt": request.prompt,
            "message": "NexusFlow multi-agent workflow initialized.",
        },
    )

    current_node = "init"
    final_generated_code: Dict[str, str] = {}
    final_review_feedback = ""
    final_iterations = 0
    final_execution_result: Optional[Dict[str, Any]] = None
    final_iteration_history: List[Dict[str, Any]] = []

    try:
        async for event in nexus_graph.astream_events(initial_state, config=config, version="v2"):
            event_type = event.get("event")
            metadata = event.get("metadata", {})
            node_name = metadata.get("langgraph_node")

            if node_name and node_name != current_node:
                current_node = node_name
                yield format_sse_event(
                    "node_start",
                    {
                        "session_id": session_id,
                        "node": current_node,
                        "message": f"Agent '{current_node}' is active.",
                    },
                )

            if event_type == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                token_text = getattr(chunk, "content", "")
                if token_text and isinstance(token_text, str):
                    yield format_sse_event(
                        "token",
                        {
                            "session_id": session_id,
                            "node": current_node,
                            "chunk": token_text,
                        },
                    )

            elif event_type == "on_chain_end" and node_name in ("coder", "reviewer"):
                output_data = event.get("data", {}).get("output")
                if isinstance(output_data, dict):
                    if "generated_code" in output_data and output_data["generated_code"]:
                        final_generated_code = output_data["generated_code"]
                        final_iterations = output_data.get("iterations", final_iterations)
                        final_execution_result = output_data.get("execution_result")
                        if "iteration_history" in output_data:
                            final_iteration_history = output_data["iteration_history"]

                        yield format_sse_event(
                            "code_update",
                            {
                                "session_id": session_id,
                                "node": "coder",
                                "iterations": final_iterations,
                                "generated_code": final_generated_code,
                                "execution_result": final_execution_result,
                                "iteration_history": final_iteration_history,
                            },
                        )

                    if "review_feedback" in output_data and output_data["review_feedback"]:
                        final_review_feedback = output_data["review_feedback"]
                        yield format_sse_event(
                            "review_update",
                            {
                                "session_id": session_id,
                                "node": "reviewer",
                                "iterations": final_iterations,
                                "review_feedback": final_review_feedback,
                            },
                        )

        # Log completion with code JSON in MS SQL Server
        log_execution(
            session_id=session_id,
            prompt=request.prompt,
            status="completed",
            iterations=final_iterations or 1,
            files_count=len(final_generated_code),
            review_feedback=final_review_feedback if isinstance(final_review_feedback, str) else json.dumps(final_review_feedback),
            generated_files=final_generated_code,
        )

        # Run automated security audit on synthesized code
        security_report = audit_codebase_security(final_generated_code) if final_generated_code else None

        yield format_sse_event(
            "complete",
            {
                "session_id": session_id,
                "node": "complete",
                "status": "completed",
                "iterations": final_iterations or 1,
                "generated_code": final_generated_code,
                "review_feedback": final_review_feedback,
                "execution_result": final_execution_result,
                "iteration_history": final_iteration_history,
                "security_report": security_report,
                "message": "Workflow successfully finished and verified.",
            },
        )

    except Exception as exc:
        logger.exception(f"[Workflow Stream] Error during execution: {exc}")
        log_execution(
            session_id=session_id,
            prompt=request.prompt,
            status="error",
            iterations=final_iterations or 1,
            files_count=len(final_generated_code),
            review_feedback=str(exc),
            generated_files=final_generated_code,
        )

        yield format_sse_event(
            "error",
            {
                "session_id": session_id,
                "node": "error",
                "error": str(exc),
                "message": "Workflow encountered an unexpected error during execution.",
            },
        )


@router.post("/stream", summary="Stream real-time multi-agent workflow events via SSE")
async def stream_workflow(request: ChatRequest) -> StreamingResponse:
    """Streams multi-agent workflow events using SSE."""
    return StreamingResponse(
        generate_workflow_events(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/execute", response_model=ChatResponse, summary="Synchronous workflow execution")
async def execute_workflow(request: ChatRequest) -> ChatResponse:
    """Synchronously executes the multi-agent graph."""
    session_id = request.session_id or str(uuid.uuid4())
    logger.info(f"[Workflow Execute] Session {session_id} initiated.")

    initial_state: GraphState = {
        "messages": [HumanMessage(content=request.prompt)],
        "generated_code": {},
        "review_feedback": "",
        "iterations": 0,
        "current_node": "init",
        "execution_result": None,
        "iteration_history": [],
        "language": request.language or "python",
    }

    config = {"configurable": {"thread_id": session_id}}

    try:
        result_state = await nexus_graph.ainvoke(initial_state, config=config)

        generated_code = result_state.get("generated_code", {})
        review_feedback = result_state.get("review_feedback", "")
        iterations = result_state.get("iterations", 1)
        execution_result = result_state.get("execution_result")

        log_execution(
            session_id=session_id,
            prompt=request.prompt,
            status="completed",
            iterations=iterations,
            files_count=len(generated_code),
            review_feedback=str(review_feedback),
            generated_files=generated_code,
        )

        return ChatResponse(
            session_id=session_id,
            prompt=request.prompt,
            status="completed",
            iterations=iterations,
            current_node="complete",
            generated_code=generated_code,
            review_feedback=review_feedback,
            execution_result=execution_result,
        )

    except Exception as exc:
        logger.exception(f"[Workflow Execute] Failure: {exc}")
        log_execution(
            session_id=session_id,
            prompt=request.prompt,
            status="error",
            iterations=1,
            files_count=0,
            review_feedback=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failure: {str(exc)}",
        )


@router.post("/validate", summary="Multi-language sandbox code validator")
async def validate_code_snippet(payload: Dict[str, Any]) -> ExecutionOutput:
    """Executes arbitrary code in the safe sandbox environment (Python, Node.js, TypeScript)."""
    code = payload.get("code")
    language = payload.get("language", "python")
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'code' attribute in request payload.",
        )

    result = run_code_validation(code, language=language)
    return ExecutionOutput(
        success=result["success"],
        exit_code=result["exit_code"],
        stdout=result["stdout"],
        stderr=result["stderr"],
        execution_time_seconds=result["execution_time_seconds"],
    )


@router.post("/security-scan", summary="Automated static security vulnerability audit")
async def security_scan_codebase(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Audits code or multi-file dictionary for security vulnerabilities."""
    files = payload.get("files")
    code = payload.get("code")

    if files and isinstance(files, dict):
        return audit_codebase_security(files)
    elif code and isinstance(code, str):
        return audit_code_security(code, file_name=payload.get("file_name", "main.py"))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must include either 'files' dictionary or 'code' string.",
        )


@router.get("/history", summary="Query past execution history from MS SQL Server")
async def get_history(limit: int = Query(default=20, ge=1, le=100)) -> List[Dict[str, Any]]:
    """Returns chronological workflow executions stored in SQL Server."""
    return get_execution_history(limit=limit)


@router.get("/history/{session_id}", summary="Get full session record and generated files")
async def get_session_detail(session_id: str) -> Dict[str, Any]:
    """Retrieves full details and generated files for a given session ID."""
    session_data = get_execution_by_session_id(session_id)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No execution record found for session ID: {session_id}",
        )
    return session_data


@router.get("/analytics", summary="Aggregated platform performance analytics")
async def get_analytics() -> Dict[str, Any]:
    """Returns aggregated platform metrics from MS SQL Server."""
    return get_analytics_metrics()
