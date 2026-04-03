from app.application.ports.runtime_status_gateway import RuntimeStatusGateway
from app.domain.health import HealthStatus


class HealthCheckUseCase:
    def __init__(self, runtime_gateway: RuntimeStatusGateway):
        self._runtime_gateway = runtime_gateway

    def execute(self) -> HealthStatus:
        return HealthStatus(
            status="healthy",
            version=self._runtime_gateway.get_version(),
            llm_ready=self._runtime_gateway.is_llm_ready(),
        )
