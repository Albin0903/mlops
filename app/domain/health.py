from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HealthStatus:
    status: str
    version: str
    llm_ready: bool
