from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderSelection:
    alias: str
    provider: str
    model: str
