import logging
from groq import Groq, RateLimitError as GroqRateLimitError, APIConnectionError as GroqConnError
import google.genai as genai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable

from src.config.settings import settings
from src.resilience.circuit_breaker import CircuitBreaker
from src.resilience.retry_policy import llm_retry

logger = logging.getLogger(__name__)


class AllProvidersFailedError(Exception):
    """Raised when every provider in the fallback chain has failed."""
    pass


class LLMProvider:
    """Wraps a single provider's SDK behind a consistent .generate() interface."""

    def __init__(self, name: str, client, model: str, retryable_exceptions: tuple):
        self.name = name
        self.client = client
        self.model = model
        self.retryable_exceptions = retryable_exceptions

    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        @llm_retry(self.retryable_exceptions)
        def _call():
            if self.name == "groq":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content

            elif self.name == "gemini":
                model_instance = self.client.GenerativeModel(self.model)
                response = model_instance.generate_content(
                    prompt,
                    generation_config={"max_output_tokens": max_tokens},
                )
                return response.text

            raise ValueError(f"Unknown provider name: {self.name}")

        return _call()


class LLMFallbackManager:
    """Same interface as before — tries providers in order, skips open circuits."""

    def __init__(self, providers: list[LLMProvider], circuit_breaker: CircuitBreaker):
        self.providers = providers
        self.circuit_breaker = circuit_breaker

    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        last_error: Exception | None = None

        for provider in self.providers:
            if self.circuit_breaker.is_open(provider.name):
                logger.info(f"Skipping '{provider.name}' — circuit open")
                continue

            try:
                result = provider.generate(prompt, max_tokens=max_tokens)
                self.circuit_breaker.record_success(provider.name)
                return result
            except Exception as e:
                logger.warning(f"Provider '{provider.name}' failed: {e}")
                self.circuit_breaker.record_failure(provider.name)
                last_error = e
                continue

        raise AllProvidersFailedError(
            f"All {len(self.providers)} providers failed. Last error: {last_error}"
        ) from last_error


def build_default_llm_manager() -> LLMFallbackManager:
    """Factory: builds the manager using settings.py config — call once at app startup."""

    # genai.configure(api_key=settings.GEMINI_API_KEY)
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    groq_provider = LLMProvider(
        name="groq",
        client=Groq(api_key=settings.GROQ_API_KEY),
        model="llama-3.3-70b-versatile",
        retryable_exceptions=(GroqRateLimitError, GroqConnError),
    )
    gemini_provider = LLMProvider(
        name="gemini",
        client=client,
        model="gemini-2.0-flash",
        retryable_exceptions=(ResourceExhausted, ServiceUnavailable),
    )

    providers = (
        [groq_provider, gemini_provider]
        if settings.primary_llm_provider == "groq"
        else [gemini_provider, groq_provider]
    )

    return LLMFallbackManager(providers=providers, circuit_breaker=CircuitBreaker())