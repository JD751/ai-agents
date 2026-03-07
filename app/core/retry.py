import openai
from tenacity import (
    AsyncRetrying,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Centralised here so switching LLM provider means changing one file.
_RETRYABLE = (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError)

_WAIT = wait_exponential(multiplier=1, min=1, max=10)
_STOP = stop_after_attempt(3)

llm_retry = retry(
    retry=retry_if_exception_type(_RETRYABLE),
    wait=_WAIT,
    stop=_STOP,
    reraise=True,
)


def async_llm_retry() -> AsyncRetrying:
    """Return a configured AsyncRetrying context manager for use with async LLM calls."""
    return AsyncRetrying(
        retry=retry_if_exception_type(_RETRYABLE),
        wait=_WAIT,
        stop=_STOP,
        reraise=True,
    )
