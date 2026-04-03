from app.domain.provider import ProviderSelection
from app.services.provider_registry import PROVIDER_MODELS, resolve_provider_alias, resolve_provider_name


class RegistryProviderResolverGateway:
    def resolve(self, provider_alias: str) -> ProviderSelection:
        normalized_alias = resolve_provider_alias(provider_alias)
        model = PROVIDER_MODELS.get(normalized_alias, normalized_alias)
        provider = resolve_provider_name(normalized_alias, model)
        return ProviderSelection(alias=normalized_alias, provider=provider, model=model)
