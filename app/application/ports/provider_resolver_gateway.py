from typing import Protocol

from app.domain.provider import ProviderSelection


class ProviderResolverGateway(Protocol):
    def resolve(self, provider_alias: str) -> ProviderSelection: ...
