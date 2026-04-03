"""Tests unitaires des politiques partagées LLM."""

import httpx

from app.services.llm.policies import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    GEMINI_THINKING_LEVEL,
    GROQ_RETRY_ATTEMPTS,
    OLLAMA_NUM_PREDICT,
    OLLAMA_TIMEOUT,
    groq_stream_retry_policy,
)


def test_default_inference_constants_are_stable():
    assert DEFAULT_TEMPERATURE == 0.2
    assert DEFAULT_MAX_TOKENS == 1024
    assert DEFAULT_TOP_P == 1
    assert OLLAMA_NUM_PREDICT == 384


def test_gemini_thinking_level_default():
    assert GEMINI_THINKING_LEVEL == "LOW"


def test_ollama_timeout_is_httpx_timeout():
    assert isinstance(OLLAMA_TIMEOUT, httpx.Timeout)


def test_groq_retry_policy_is_callable_decorator():
    decorator = groq_stream_retry_policy()

    assert callable(decorator)
    assert GROQ_RETRY_ATTEMPTS == 3
