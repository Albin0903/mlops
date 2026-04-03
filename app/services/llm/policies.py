import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TOP_P = 1

GROQ_RETRY_ATTEMPTS = 3
GROQ_RETRY_MULTIPLIER = 1
GROQ_RETRY_MIN_SECONDS = 2
GROQ_RETRY_MAX_SECONDS = 10

GEMINI_THINKING_LEVEL = "LOW"

OLLAMA_NUM_PREDICT = 384
OLLAMA_TIMEOUT = httpx.Timeout(timeout=300.0, connect=10.0)


def groq_stream_retry_policy():
    return retry(
        stop=stop_after_attempt(GROQ_RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=GROQ_RETRY_MULTIPLIER,
            min=GROQ_RETRY_MIN_SECONDS,
            max=GROQ_RETRY_MAX_SECONDS,
        ),
        reraise=True,
    )
