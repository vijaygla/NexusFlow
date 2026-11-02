"""
NexusFlow LLM Client Factory
Configures resilient ChatOpenAI instances for agents with custom timeouts and httpx clients.
"""

import httpx
from langchain_openai import ChatOpenAI
from app.config import get_settings


def get_chat_model(model_name: str = None, temperature: float = 0.2, streaming: bool = False) -> ChatOpenAI:
    """
    Returns a configured ChatOpenAI model using the Capgemini Generative Engine endpoint.
    Passes custom httpx clients to prevent stream assertion conflicts.
    """
    settings = get_settings()
    selected_model = model_name or settings.CODER_MODEL

    # Standard clean httpx client
    sync_client = httpx.Client(verify=False, timeout=60.0)
    async_client = httpx.AsyncClient(verify=False, timeout=60.0)

    return ChatOpenAI(
        model=selected_model,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=temperature,
        streaming=streaming,
        http_client=sync_client,
        http_async_client=async_client,
    )
