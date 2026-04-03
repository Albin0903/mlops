import json
from typing import Any


def parse_tool_arguments(raw_args: Any) -> Any:
    if isinstance(raw_args, str):
        try:
            return json.loads(raw_args)
        except json.JSONDecodeError:
            return raw_args
    return raw_args


def build_tool_calls_result(calls: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "tool_calls", "calls": calls}


def build_text_result(content: str | None) -> dict[str, Any]:
    return {"type": "text", "content": content or ""}
