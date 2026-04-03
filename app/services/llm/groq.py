from typing import Any, AsyncGenerator

from app.core.config import settings
from app.services.llm.base import BaseLLMProvider
from app.services.llm.common import build_text_result, build_tool_calls_result, parse_tool_arguments
from app.services.llm.policies import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    groq_stream_retry_policy,
)


class GroqProvider(BaseLLMProvider):
    def __init__(self):
        from groq import AsyncGroq

        self.client = AsyncGroq(api_key=settings.groq_api_key)

    async def stream_response(
        self,
        prompt: str,
        system_message: str,
        model: str,
        thinking: str | bool | None = None,
        json_format: bool = False,
    ) -> AsyncGenerator[tuple[str, int, int], None]:
        @groq_stream_retry_policy()
        async def _call():
            kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                "temperature": DEFAULT_TEMPERATURE,
                "max_tokens": DEFAULT_MAX_TOKENS,
                "top_p": DEFAULT_TOP_P,
                "stream": True,
            }
            if json_format:
                kwargs["response_format"] = {"type": "json_object"}
            return await self.client.chat.completions.create(**kwargs)

        stream = await _call()
        input_tokens = 0
        output_tokens = 0
        async for chunk in stream:
            if hasattr(chunk, "x_groq") and chunk.x_groq and hasattr(chunk.x_groq, "usage"):
                usage = chunk.x_groq.usage
                input_tokens = getattr(usage, "prompt_tokens", 0)
                output_tokens = getattr(usage, "completion_tokens", 0)

            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content, input_tokens, output_tokens

    async def execute_agent_call(
        self,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        thinking: str | bool | None = None,
    ) -> dict[str, Any]:
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": DEFAULT_TEMPERATURE,
            "max_tokens": DEFAULT_MAX_TOKENS,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = await self.client.chat.completions.create(**kwargs)
        except Exception as e:
            if tools and getattr(e, "code", None) == "tool_use_failed":
                strict_messages = list(messages)
                strict_messages.append(
                    {
                        "role": "user",
                        "content": "Important: appelle exactement UNE fonction valide. JSON strict. Pas de balises XML.",
                    }
                )
                kwargs["messages"] = strict_messages
                response = await self.client.chat.completions.create(**kwargs)
            else:
                raise

        message = response.choices[0].message
        if hasattr(message, "tool_calls") and message.tool_calls:
            calls = []
            for tc in message.tool_calls:
                args = parse_tool_arguments(tc.function.arguments)
                calls.append({"name": tc.function.name, "args": args})
            return build_tool_calls_result(calls)

        return build_text_result(message.content)
