"""
NexusFlow Chat & Workflow Schemas
Pydantic schemas for HTTP requests, responses, and SSE stream events.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
import uuid


class ChatRequest(BaseModel):
    """Payload sent by the client to initiate or continue a workflow run."""
    prompt: str = Field(..., min_length=1, description="User instruction or specification prompt")
    session_id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the workflow thread/session"
    )
    max_iterations: Optional[int] = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum refinement iterations before terminating"
    )
    language: Optional[str] = Field(
        default="python",
        description="Target programming language for generation and execution"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt": "Create a robust Python module for calculating Fibonacci numbers with LRU caching and unit tests.",
                "session_id": "session-12345",
                "max_iterations": 3,
                "language": "python"
            }
        }
    }


class ExecutionOutput(BaseModel):
    """Output captured from code execution."""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time_seconds: Optional[float] = None


class ChatResponse(BaseModel):
    """Structured response returned by synchronous workflow execution."""
    session_id: str
    prompt: str
    status: str = Field(..., description="Workflow status: 'completed', 'max_iterations_reached', 'error'")
    iterations: int
    current_node: str
    generated_code: Dict[str, str] = Field(default_factory=dict, description="File map of synthesized code")
    review_feedback: Optional[Union[str, List[str]]] = None
    execution_result: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "session-12345",
                "prompt": "Create a Fibonacci function...",
                "status": "completed",
                "iterations": 1,
                "current_node": "complete",
                "generated_code": {
                    "fibonacci.py": "def fib(n): ...",
                    "test_fibonacci.py": "import unittest ..."
                },
                "review_feedback": "Code is clean, well-tested, and adheres to PEP-8 standards.",
                "execution_result": {
                    "success": True,
                    "exit_code": 0,
                    "stdout": "All tests passed.\n"
                }
            }
        }
    }


class StreamEventPayload(BaseModel):
    """Typed payload structure for SSE events."""
    event: str = Field(..., description="Event type: 'node_start', 'token', 'code_update', 'review_update', 'complete', 'error'")
    node: str = Field(..., description="Active graph node name")
    session_id: str
    data: Any = Field(default=None, description="Event data content")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
