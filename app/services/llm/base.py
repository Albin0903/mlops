from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator


class BaseLLMProvider(ABC):
    @abstractmethod
    def stream_response(
        self, prompt: str, system_message: str, model: str, thinking: str | bool | None = None
    ) -> AsyncGenerator[tuple[str, int, int], None]:
        """Stream response and yield (content, input_tokens, output_tokens)"""
        pass

    @abstractmethod
    async def execute_agent_call(
        self,
        messages: list[dict[str, str]],
        model: str,
        tools: list[dict[str, Any]] = None,
        thinking: str | bool | None = None,
    ) -> dict[str, Any]:
        """Execute a non-streaming agent call with optional tools"""
        pass
