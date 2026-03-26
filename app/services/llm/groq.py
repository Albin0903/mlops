from typing import Any, AsyncGenerator

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.services.llm.base import BaseLLMProvider


class GroqProvider(BaseLLMProvider):
    def __init__(self):
        from groq import AsyncGroq

        self.client = AsyncGroq(api_key=settings.groq_api_key)

    async def stream_response(
        self, prompt: str, system_message: str, model: str, thinking: str | bool | None = None
    ) -> AsyncGenerator[tuple[str, int, int], None]:
        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
        async def _call():
            return await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=1024,
                top_p=1,
                stream=True,
            )

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
        messages: list[dict[str, str]],
        model: str,
        tools: list[dict[str, Any]] = None,
        thinking: str | bool | None = None,
    ) -> dict[str, Any]:
        import json

        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1024,
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
                args = tc.function.arguments
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        pass
                calls.append({"name": tc.function.name, "args": args})
            return {"type": "tool_calls", "calls": calls}

        return {"type": "text", "content": message.content or ""}
