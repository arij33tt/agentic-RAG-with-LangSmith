from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type


def llm_retry(exceptions: tuple = (Exception,)):
    """
    Reusable retry decorator for LLM provider calls.
    3 attempts, exponential backoff with jitter, only retries on
    the exception types you specify (pass the SDK's rate-limit/
    connection error types, not a bare catch-all, when using this).
    """
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=8),
        retry=retry_if_exception_type(exceptions),
        reraise=True,
    )