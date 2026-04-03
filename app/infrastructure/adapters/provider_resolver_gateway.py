from app.domain.provider import ProviderSelection
from app.services.provider_registry import PROVIDER_MODELS, resolve_provider_name


class RegistryProviderResolverGateway:
    def resolve(self, provider_alias: str) -> ProviderSelection:
        model = PROVIDER_MODELS.get(provider_alias, provider_alias)
        provider = resolve_provider_name(provider_alias, model)
        return ProviderSelection(alias=provider_alias, provider=provider, model=model)
