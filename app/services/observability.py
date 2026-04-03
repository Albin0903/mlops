from typing import Any

from loguru import logger

PROMETHEUS_METRICS: dict[str, Any] = {}


def _get_prometheus_metric(metric_name: str, factory):
    if metric_name not in PROMETHEUS_METRICS:
        PROMETHEUS_METRICS[metric_name] = factory()
    return PROMETHEUS_METRICS[metric_name]


class LLMObservability:
    def start_generation(
        self,
        *,
        enabled: bool,
        mode: str,
        provider: str,
        model: str,
        prompt: str,
        system_message: str,
    ) -> Any | None:
        if not enabled:
            return None

        try:
            from langfuse import get_client

            langfuse: Any = get_client()
            return langfuse.generation(
                name=f"llm-{mode}-{provider}",
                model=model,
                input={"prompt": prompt, "system_message": system_message},
                metadata={"provider": provider, "mode": mode, "model": model},
            )
        except Exception as exc:
            logger.warning(f"langfuse init failed : {exc}")
            return None

    def mark_generation_error(self, generation: Any | None, error: Exception) -> None:
        if generation is None:
            return
        generation.update(level="ERROR", status_message=str(error))

    def end_generation(
        self,
        generation: Any | None,
        output: str,
        input_tokens: int,
        output_tokens: int,
        latency_seconds: float,
    ) -> None:
        if generation is None:
            return

        try:
            generation.end(
                output=output,
                usage={"input": input_tokens, "output": output_tokens},
                metadata={"latency_seconds": round(latency_seconds, 3)},
            )
        except Exception as exc:
            logger.warning(f"langfuse logging end failed : {exc}")

    def record_metrics(self, provider: str, model: str, mode: str, in_tok: int, out_tok: int, latency: float) -> None:
        try:
            from prometheus_client import Counter, Histogram

            llm_requests_total = _get_prometheus_metric(
                "llm_requests_total",
                lambda: Counter("llm_requests_total", "total requests", ["provider", "model", "mode"]),
            )
            llm_tokens_total = _get_prometheus_metric(
                "llm_tokens_total",
                lambda: Counter("llm_tokens_total", "total tokens", ["provider", "model", "type"]),
            )
            llm_latency_seconds = _get_prometheus_metric(
                "llm_latency_seconds",
                lambda: Histogram("llm_latency_seconds", "latency", ["provider", "model"]),
            )

            llm_requests_total.labels(provider=provider, model=model, mode=mode).inc()
            llm_tokens_total.labels(provider=provider, model=model, type="input").inc(in_tok)
            llm_tokens_total.labels(provider=provider, model=model, type="output").inc(out_tok)
            llm_latency_seconds.labels(provider=provider, model=model).observe(latency)
        except Exception:
            pass
