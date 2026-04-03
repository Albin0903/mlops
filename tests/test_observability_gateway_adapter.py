"""Tests unitaires de l'adapter observabilite."""

from app.domain.usage import TokenUsage
from app.infrastructure.adapters.observability_gateway import DefaultObservabilityGateway


class FakeObservability:
    def __init__(self):
        self.start_calls: list[dict] = []
        self.error_mark_calls: list[dict] = []
        self.end_calls: list[dict] = []
        self.metrics_calls: list[dict] = []

    def start_generation(self, **kwargs):
        self.start_calls.append(kwargs)
        return "gen"

    def mark_generation_error(self, generation, error):
        self.error_mark_calls.append({"generation": generation, "error": error})

    def end_generation(self, generation, output, input_tokens, output_tokens, latency_seconds):
        self.end_calls.append(
            {
                "generation": generation,
                "output": output,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_seconds": latency_seconds,
            }
        )

    def record_metrics(self, provider, model, mode, in_tok, out_tok, latency):
        self.metrics_calls.append(
            {
                "provider": provider,
                "model": model,
                "mode": mode,
                "in_tok": in_tok,
                "out_tok": out_tok,
                "latency": latency,
            }
        )


def test_default_observability_gateway_delegates_start_end_and_success():
    fake = FakeObservability()
    gateway = DefaultObservabilityGateway(observability=fake)

    generation = gateway.start_generation(
        enabled=True,
        mode="doc",
        provider="groq",
        model="llama-3.1-8b-instant",
        prompt="prompt",
        system_message="system",
    )

    usage = TokenUsage(input_tokens=10, output_tokens=20)
    gateway.record_success(
        provider="groq",
        model="llama-3.1-8b-instant",
        mode="doc",
        usage=usage,
        latency_seconds=0.5,
    )
    gateway.end_generation(generation=generation, output="ok", usage=usage, latency_seconds=0.5)

    assert generation == "gen"
    assert len(fake.start_calls) == 1
    assert fake.start_calls[0]["provider"] == "groq"
    assert len(fake.metrics_calls) == 1
    assert fake.metrics_calls[0]["in_tok"] == 10
    assert fake.metrics_calls[0]["out_tok"] == 20
    assert len(fake.end_calls) == 1
    assert fake.end_calls[0]["generation"] == "gen"


def test_default_observability_gateway_marks_error():
    fake = FakeObservability()
    gateway = DefaultObservabilityGateway(observability=fake)

    gateway.mark_generation_error("gen", "boom")

    assert len(fake.error_mark_calls) == 1
    assert fake.error_mark_calls[0]["generation"] == "gen"
    assert str(fake.error_mark_calls[0]["error"]) == "boom"
