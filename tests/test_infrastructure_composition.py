"""Tests unitaires de la couche infrastructure (adapters + composition)."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.application.use_cases.analyze_stream import AnalyzeStreamUseCase
from app.application.use_cases.execute_agent_call import ExecuteAgentCallUseCase
from app.application.use_cases.generate_full_response import GenerateFullResponseUseCase
from app.application.use_cases.health_check import HealthCheckUseCase
from app.application.use_cases.resolve_provider import ResolveProviderUseCase
from app.domain.provider import ProviderSelection
from app.infrastructure import composition
from app.infrastructure.adapters.llm_gateway_adapter import LLMServiceGateway


def test_llm_service_gateway_get_system_prompt_delegates():
    llm_service = Mock()
    llm_service.get_system_prompt.return_value = "system"

    gateway = LLMServiceGateway(llm_service=llm_service)
    result = gateway.get_system_prompt("doc", "python")

    assert result == "system"
    llm_service.get_system_prompt.assert_called_once_with("doc", "python")


@pytest.mark.asyncio
async def test_llm_service_gateway_stream_response_delegates():
    async def fake_stream():
        yield "chunk-1"
        yield "chunk-2"

    llm_service = Mock()
    llm_service.get_streaming_response.return_value = fake_stream()

    gateway = LLMServiceGateway(llm_service=llm_service)
    chunks = [
        chunk
        async for chunk in gateway.stream_response(
            prompt="prompt",
            system_message="system",
            mode="doc",
            provider_selection=ProviderSelection(
                alias="medium",
                provider="groq",
                model="llama-3.3-70b-versatile",
            ),
        )
    ]

    assert chunks == ["chunk-1", "chunk-2"]
    llm_service.get_streaming_response.assert_called_once_with(
        prompt="prompt",
        system_message="system",
        mode="doc",
        provider="medium",
        thinking=None,
        json_format=False,
        resolved_provider="groq",
        resolved_model="llama-3.3-70b-versatile",
    )


@pytest.mark.asyncio
async def test_llm_service_gateway_execute_agent_call_delegates():
    llm_service = Mock()
    llm_service.execute_agent_call = AsyncMock(return_value={"type": "text", "content": "ok"})

    gateway = LLMServiceGateway(llm_service=llm_service)
    result = await gateway.execute_agent_call(
        prompt="prompt",
        system_message="system",
        messages=None,
        tools=[{"type": "function"}],
        provider_selection=ProviderSelection(
            alias="medium",
            provider="groq",
            model="llama-3.3-70b-versatile",
        ),
        thinking="off",
    )

    assert result["type"] == "text"
    llm_service.execute_agent_call.assert_called_once_with(
        prompt="prompt",
        system_message="system",
        messages=None,
        tools=[{"type": "function"}],
        provider="medium",
        thinking="off",
        resolved_provider="groq",
        resolved_model="llama-3.3-70b-versatile",
    )


def test_composition_builds_and_caches_use_cases():
    composition.get_observability_gateway.cache_clear()
    composition.get_llm_provider_registry.cache_clear()
    composition.get_llm_service.cache_clear()
    composition.get_analyze_stream_use_case.cache_clear()
    composition.get_execute_agent_call_use_case.cache_clear()
    composition.get_generate_full_response_use_case.cache_clear()
    composition.get_health_check_use_case.cache_clear()
    composition.get_resolve_provider_use_case.cache_clear()

    observability_1 = composition.get_observability_gateway()
    observability_2 = composition.get_observability_gateway()
    provider_registry_1 = composition.get_llm_provider_registry()
    provider_registry_2 = composition.get_llm_provider_registry()
    llm_1 = composition.get_llm_service()
    llm_2 = composition.get_llm_service()
    analyze_1 = composition.get_analyze_stream_use_case()
    analyze_2 = composition.get_analyze_stream_use_case()
    execute_agent_1 = composition.get_execute_agent_call_use_case()
    execute_agent_2 = composition.get_execute_agent_call_use_case()
    generate_full_1 = composition.get_generate_full_response_use_case()
    generate_full_2 = composition.get_generate_full_response_use_case()
    health_1 = composition.get_health_check_use_case()
    health_2 = composition.get_health_check_use_case()
    resolve_provider_1 = composition.get_resolve_provider_use_case()
    resolve_provider_2 = composition.get_resolve_provider_use_case()

    assert observability_1 is observability_2
    assert provider_registry_1 is provider_registry_2
    assert llm_1._provider_getter.__self__ is provider_registry_1
    assert llm_1 is llm_2
    assert isinstance(analyze_1, AnalyzeStreamUseCase)
    assert isinstance(execute_agent_1, ExecuteAgentCallUseCase)
    assert isinstance(generate_full_1, GenerateFullResponseUseCase)
    assert isinstance(health_1, HealthCheckUseCase)
    assert isinstance(resolve_provider_1, ResolveProviderUseCase)
    assert analyze_1 is analyze_2
    assert execute_agent_1 is execute_agent_2
    assert generate_full_1 is generate_full_2
    assert health_1 is health_2
    assert resolve_provider_1 is resolve_provider_2
