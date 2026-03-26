import json
import re
import shutil
import subprocess
from typing import Any, AsyncGenerator

import httpx
from loguru import logger

from app.core.config import settings
from app.services.llm.base import BaseLLMProvider

# Timeout long pour les modeles locaux (chargement + inference)
OLLAMA_TIMEOUT = httpx.Timeout(timeout=300.0, connect=10.0)
# Limite de securite pour le contexte Ollama. Les modeles Qwen exposes par Ollama
# annoncent une fenetre native tres large, mais on la borne selon la VRAM disponible.
MAX_NUM_CTX = 262144

THINKING_RE = re.compile(r"<think>.*?</think>", flags=re.DOTALL)
THINKING_BLOCK_RE = re.compile(r"<think>(.*?)</think>", flags=re.DOTALL)


def _normalize_thinking(thinking: str | bool | None) -> str | bool:
    if thinking is None:
        return False
    if isinstance(thinking, bool):
        return thinking

    normalized = thinking.strip().lower()
    if normalized in {"false", "off", "no", "0"}:
        return False
    if normalized in {"true", "on", "yes", "1"}:
        return True
    if normalized in {"low", "medium", "high"}:
        return normalized

    raise ValueError("thinking doit être l'une des valeurs: off, low, medium, high")


def _split_thinking_content(text: str) -> tuple[list[str], str]:
    thoughts = [block.strip() for block in THINKING_BLOCK_RE.findall(text) if block.strip()]
    visible_text = THINKING_BLOCK_RE.sub("", text).strip()
    return thoughts, visible_text


def _extract_chunk_content(data: dict[str, Any]) -> str:
    message = data.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str) and content:
            return content

    content = data.get("response")
    if isinstance(content, str) and content:
        return content

    return ""


def _parse_model_size_billion(model: str) -> float | None:
    model_name = model.split(":")[-1].lower()
    match = re.search(r"(\d+(?:\.\d+)?)\s*b\b", model_name)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _detect_total_vram_mb() -> int | None:
    if shutil.which("nvidia-smi") is None:
        return None

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        first_line = result.stdout.strip().splitlines()[0].strip()
        return int(first_line)
    except Exception:
        return None


def _select_num_ctx(model: str) -> int:
    model_size_b = _parse_model_size_billion(model)
    vram_mb = _detect_total_vram_mb()

    # Fallback conservateur sur une machine 6 Go si la VRAM n'est pas detectable.
    if vram_mb is None:
        vram_mb = 6144

    # Profil qualite: on privilegie un contexte plus large pour de meilleurs resultats
    # sur des taches comme Pedantix, tout en restant borné par la VRAM disponible.
    if vram_mb <= 4096:
        target = 4096 if model_size_b is not None and model_size_b <= 3 else 2048
    elif vram_mb <= 6144:
        target = (
            8192
            if model_size_b is not None and model_size_b <= 3
            else 4096
            if model_size_b is not None and model_size_b <= 9
            else 2048
        )
    elif vram_mb <= 8192:
        target = (
            12288
            if model_size_b is not None and model_size_b <= 3
            else 8192
            if model_size_b is not None and model_size_b <= 9
            else 4096
        )
    else:
        target = (
            16384
            if model_size_b is not None and model_size_b <= 3
            else 12288
            if model_size_b is not None and model_size_b <= 9
            else 8192
        )

    return min(target, MAX_NUM_CTX)


class OllamaProvider(BaseLLMProvider):
    def __init__(self):
        self.base_url = f"{settings.ollama_base_url}/api"

    async def stream_response(
        self, prompt: str, system_message: str, model: str, thinking: str | bool | None = None
    ) -> AsyncGenerator[tuple[str, int, int], None]:
        num_ctx = _select_num_ctx(model)
        normalized_thinking = _normalize_thinking(thinking)
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_message}, {"role": "user", "content": prompt}],
            "stream": True,
            "think": normalized_thinking,
            "options": {"num_ctx": num_ctx},
        }

        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT, trust_env=False) as client:
            target_url = f"{self.base_url}/chat"
            logger.info(
                f"ollama stream | url={target_url} | model={model} | ctx={num_ctx} | think={normalized_thinking}"
            )

            async with client.stream("POST", target_url, json=payload) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    logger.error(f"ollama error {response.status_code} | body={body[:200]}")
                    yield f"erreur ollama : {response.status_code}", 0, 0
                    return

                print("  [ollama] ", end="", flush=True)
                chunk_count = 0
                streamed_text = []

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        line = line.removeprefix("data: ").strip()
                    if line == "[DONE]":
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    content = _extract_chunk_content(data)
                    if content:
                        if chunk_count == 0:
                            logger.info("ollama | first token received")
                        chunk_count += 1
                        streamed_text.append(content)

                        thoughts, visible_text = _split_thinking_content(content)
                        if thoughts and normalized_thinking:
                            for thought in thoughts:
                                print(f"\n  [thinking] {thought}", end="", flush=True)

                        output_text = visible_text if thoughts and normalized_thinking else content

                        print(output_text, end="", flush=True)
                        usage = data.get("prompt_eval_count", 0)
                        completion_usage = data.get("eval_count", 0)
                        yield content, usage, completion_usage

                if chunk_count == 0:
                    logger.warning("ollama stream yielded no visible chunks, retrying in non-stream mode")
                    fallback_payload = dict(payload)
                    fallback_payload["stream"] = False
                    fallback_response = await client.post(target_url, json=fallback_payload)
                    if fallback_response.status_code != 200:
                        body = fallback_response.text[:200]
                        logger.error(f"ollama fallback error {fallback_response.status_code} | body={body}")
                        yield f"erreur ollama : {fallback_response.status_code}", 0, 0
                        return

                    fallback_data = fallback_response.json()
                    fallback_content = _extract_chunk_content(fallback_data)
                    fallback_message = fallback_content.strip()
                    if fallback_message:
                        thoughts, visible_text = _split_thinking_content(fallback_message)
                        if thoughts and normalized_thinking:
                            for thought in thoughts:
                                print(f"\n  [thinking] {thought}", end="", flush=True)

                        print(
                            (visible_text if thoughts and normalized_thinking else fallback_message), end="", flush=True
                        )
                        prompt_eval = fallback_data.get("prompt_eval_count", 0)
                        eval_count = fallback_data.get("eval_count", 0)
                        yield fallback_message, prompt_eval, eval_count

                print()  # Saut de ligne final
                logger.info(f"ollama stream done | {chunk_count} tokens generated")

    async def execute_agent_call(
        self,
        messages: list[dict[str, str]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        thinking: str | bool | None = None,
    ) -> dict[str, Any]:
        num_ctx = _select_num_ctx(model)
        normalized_thinking = _normalize_thinking(thinking)
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 1, "num_ctx": num_ctx},
            "think": normalized_thinking,
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT, trust_env=False) as client:
            target_url = f"{self.base_url}/chat"
            response = await client.post(target_url, json=payload)
            data = response.json()
            message = data.get("message", {})

            content = message.get("content", "")
            # Nettoyage du thinking residuel
            content = THINKING_RE.sub("", content).strip()

            if not content:
                content = _extract_chunk_content(data).strip()

            if message.get("tool_calls"):
                calls = []
                for tc in message["tool_calls"]:
                    calls.append({"name": tc["function"]["name"], "args": tc["function"]["arguments"]})
                return {"type": "tool_calls", "calls": calls}

            return {"type": "text", "content": content}
