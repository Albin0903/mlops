from app.application.ports.provider_resolver_gateway import ProviderResolverGateway
from app.domain.provider import ProviderSelection


class ResolveProviderUseCase:
    def __init__(self, provider_resolver_gateway: ProviderResolverGateway):
        self._provider_resolver_gateway = provider_resolver_gateway

    def execute(self, provider_alias: str) -> ProviderSelection:
        return self._provider_resolver_gateway.resolve(provider_alias)
