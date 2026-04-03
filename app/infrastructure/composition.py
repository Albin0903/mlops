from functools import lru_cache

from app.application.use_cases.analyze_stream import AnalyzeStreamUseCase
from app.application.use_cases.build_prompt import BuildPromptUseCase
from app.application.use_cases.execute_agent_call import ExecuteAgentCallUseCase
from app.application.use_cases.generate_full_response import GenerateFullResponseUseCase
from app.application.use_cases.health_check import HealthCheckUseCase
from app.application.use_cases.resolve_provider import ResolveProviderUseCase
from app.infrastructure.adapters.llm_gateway_adapter import LLMServiceGateway
from app.infrastructure.adapters.observability_gateway import DefaultObservabilityGateway
from app.infrastructure.adapters.provider_resolver_gateway import RegistryProviderResolverGateway
from app.infrastructure.adapters.runtime_status_gateway import SettingsRuntimeStatusGateway
from app.services.llm.factory import LLMProviderRegistry
from app.services.llm_service import LLMService


@lru_cache(maxsize=1)
def get_observability_gateway() -> DefaultObservabilityGateway:
    return DefaultObservabilityGateway()


@lru_cache(maxsize=1)
def get_llm_provider_registry() -> LLMProviderRegistry:
    return LLMProviderRegistry()


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    return LLMService(
        observability_gateway=get_observability_gateway(),
        provider_getter=get_llm_provider_registry().get_provider,
    )


@lru_cache(maxsize=1)
def get_analyze_stream_use_case() -> AnalyzeStreamUseCase:
    return AnalyzeStreamUseCase(
        llm_gateway=LLMServiceGateway(llm_service=get_llm_service()),
        build_prompt_use_case=BuildPromptUseCase(),
        resolve_provider_use_case=get_resolve_provider_use_case(),
    )


@lru_cache(maxsize=1)
def get_execute_agent_call_use_case() -> ExecuteAgentCallUseCase:
    return ExecuteAgentCallUseCase(
        llm_gateway=LLMServiceGateway(llm_service=get_llm_service()),
        resolve_provider_use_case=get_resolve_provider_use_case(),
    )


@lru_cache(maxsize=1)
def get_generate_full_response_use_case() -> GenerateFullResponseUseCase:
    return GenerateFullResponseUseCase(
        llm_gateway=LLMServiceGateway(llm_service=get_llm_service()),
        resolve_provider_use_case=get_resolve_provider_use_case(),
    )


@lru_cache(maxsize=1)
def get_resolve_provider_use_case() -> ResolveProviderUseCase:
    return ResolveProviderUseCase(provider_resolver_gateway=RegistryProviderResolverGateway())


@lru_cache(maxsize=1)
def get_health_check_use_case() -> HealthCheckUseCase:
    return HealthCheckUseCase(runtime_gateway=SettingsRuntimeStatusGateway())
