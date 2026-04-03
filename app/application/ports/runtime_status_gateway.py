from typing import Protocol


class RuntimeStatusGateway(Protocol):
    def get_version(self) -> str: ...

    def is_llm_ready(self) -> bool: ...
