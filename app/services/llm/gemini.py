from typing import Any, AsyncGenerator

from app.core.config import settings
from app.services.llm.base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    def __init__(self):
        from google import genai

        self.client = genai.Client(api_key=settings.gemini_api_key)

    async def stream_response(
        self, prompt: str, system_message: str, model: str, thinking: str | bool | None = None
    ) -> AsyncGenerator[tuple[str, int, int], None]:
        from google.genai import types

        full_prompt = f"{system_message}\n\n{prompt}"
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="LOW"),
        )
        response = await self.client.aio.models.generate_content_stream(
            model=model,
            contents=full_prompt,
            config=config,
        )
        print("  [gemini] ", end="", flush=True)
        async for chunk in response:
            if chunk.text:
                print(chunk.text, end="", flush=True)
                input_tokens = getattr(chunk.usage_metadata, "prompt_token_count", 0) if chunk.usage_metadata else 0
                output_tokens = (
                    getattr(chunk.usage_metadata, "candidates_token_count", 0) if chunk.usage_metadata else 0
                )
                yield chunk.text, input_tokens, output_tokens
        print()  # Final newline

    async def execute_agent_call(
        self,
        messages: list[dict[str, str]],
        model: str,
        tools: list[dict[str, Any]] = None,
        thinking: str | bool | None = None,
    ) -> dict[str, Any]:
        from google.genai import types

        formatted_contents = []
        system_instruction = None

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = (system_instruction + f"\n{content}") if system_instruction else content
            elif role == "user":
                formatted_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=content)]))
            elif role == "assistant" and content:
                formatted_contents.append(types.Content(role="model", parts=[types.Part.from_text(text=content)]))
            elif role == "assistant" and "tool_calls" in msg:
                # Handle agent thought/tool request
                parts = []
                if content:
                    parts.append(types.Part.from_text(text=content))
                for call in msg.get("tool_calls", []):
                    args_dict = json.loads(call["function"]["arguments"]) if isinstance(call["function"].get("arguments"), str) else call["function"].get("arguments", {})
                    parts.append(types.Part.from_function_call(name=call["function"]["name"], args=args_dict))
                if parts:
                    formatted_contents.append(types.Content(role="model", parts=parts))
            elif role == "tool":
                # Handle tool response
                import json
                try:
                    response_dict = json.loads(content) if isinstance(content, str) else content
                except Exception:
                    response_dict = {"result": content}
                
                # Gemini expects a dict for response, wrap it if it's a list
                if isinstance(response_dict, list):
                    response_dict = {"results": response_dict}
                    
                formatted_contents.append(
                    types.Content(
                        role="user", 
                        parts=[types.Part.from_function_response(name=msg.get("name", "unknown"), response=response_dict)]
                    )
                )

        config_kwargs = {}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if tools:
            gemini_tools = []
            for tool in tools:
                func_data = tool.get("function", {})
                func_decl = {"name": func_data.get("name"), "description": func_data.get("description")}
                if func_data.get("parameters"):
                    func_decl["parameters"] = func_data.get("parameters")
                gemini_tools.append({"function_declarations": [func_decl]})
            config_kwargs["tools"] = gemini_tools

        config = types.GenerateContentConfig(**config_kwargs)
        response = await self.client.aio.models.generate_content(
            model=model, contents=formatted_contents, config=config
        )

        if response.candidates and response.candidates[0].content.parts:
            calls = []
            for part in response.candidates[0].content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    calls.append({"name": part.function_call.name, "args": part.function_call.args})
            if calls:
                return {"type": "tool_calls", "calls": calls}

        return {"type": "text", "content": response.text}
