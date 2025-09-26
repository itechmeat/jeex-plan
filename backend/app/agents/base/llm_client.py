"""
LLM client with retry logic and circuit breakers.
Supports multiple LLM providers with failover.
"""

import os
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_vault_settings
from app.core.logger import get_logger

from ..contracts.base import LLMError

logger = get_logger()


def _retryable_exc(e: Exception) -> bool:
    if isinstance(e, httpx.RequestError):
        return True
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        return status == 429 or 500 <= status < 600
    return False


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker implementation for LLM API protection."""

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED

    async def call(
        self,
        func: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time < self.timeout:
                raise LLMError(
                    message="Circuit breaker is OPEN",
                    agent_type="llm_client",
                    correlation_id=kwargs.get("correlation_id", "unknown"),
                    details={"state": self.state, "failure_count": self.failure_count},
                )
            else:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as _e:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Handle successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    def __init__(
        self, provider: LLMProvider, circuit_breaker: CircuitBreaker | None = None
    ) -> None:
        self.provider = provider
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.logger = get_logger(f"llm.{provider}")

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Generate text completion."""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=16),
        retry=retry_if_exception(_retryable_exc),
        before_sleep=before_sleep_log(logger, "WARNING"),
    )
    async def _make_request(
        self,
        messages: list[dict[str, str]],
        model: str,
        correlation_id: str,
        max_tokens: int | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Make request with retry logic."""
        return await self.circuit_breaker.call(
            self._internal_generate,
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            correlation_id=correlation_id,
            **kwargs,
        )

    @abstractmethod
    async def _internal_generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        correlation_id: str,
        max_tokens: int | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Internal implementation of text generation."""


class OpenAIClient(LLMClient):
    """OpenAI API client with retry and circuit breaker."""

    def __init__(
        self,
        api_key: str | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        request_timeout_s: float = 30.0,
    ) -> None:
        super().__init__(LLMProvider.OPENAI, circuit_breaker)
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
        self.request_timeout_s = request_timeout_s

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4",
        max_tokens: int | None = None,
        temperature: float = 0.7,
        correlation_id: str = "unknown",
        **kwargs: Any,
    ) -> str:
        """Generate text using OpenAI API."""
        return await self._make_request(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            correlation_id=correlation_id,
            **kwargs,
        )

    async def _internal_generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        correlation_id: str,
        max_tokens: int | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Internal OpenAI API call."""
        if not self.api_key:
            raise LLMError(
                message="OpenAI API key not configured",
                agent_type="openai_client",
                correlation_id=correlation_id,
            )

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.request_timeout_s) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()

                if "choices" not in data or not data["choices"]:
                    raise LLMError(
                        message="No choices in OpenAI response",
                        agent_type="openai_client",
                        correlation_id=correlation_id,
                        details={"response": data},
                    )

                content = data["choices"][0]["message"]["content"]
                self.logger.info(
                    "OpenAI API call successful",
                    model=model,
                    correlation_id=correlation_id,
                    tokens_used=data.get("usage", {}).get("total_tokens", 0),
                )

                return content

        except httpx.HTTPStatusError as e:
            truncated = (e.response.text or "")[:512]
            self.logger.exception(
                "OpenAI API HTTP error",
                status_code=e.response.status_code,
                response_text_truncated=truncated,
                correlation_id=correlation_id,
            )
            raise LLMError(
                message=f"OpenAI API HTTP error: {e.response.status_code}",
                agent_type="openai_client",
                correlation_id=correlation_id,
                details={
                    "status_code": e.response.status_code,
                    "response_truncated": truncated,
                },
            ) from e
        except httpx.RequestError as e:
            self.logger.exception(
                "OpenAI API request error",
                correlation_id=correlation_id,
            )
            raise LLMError(
                message=f"OpenAI API request failed: {e!s}",
                agent_type="openai_client",
                correlation_id=correlation_id,
                details={"error": str(e)},
            ) from e


class AnthropicClient(LLMClient):
    """Anthropic/Claude API client with retry and circuit breaker."""

    def __init__(
        self,
        api_key: str | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        request_timeout_s: float = 30.0,
    ) -> None:
        super().__init__(LLMProvider.ANTHROPIC, circuit_breaker)
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1"
        self.request_timeout_s = request_timeout_s

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str = "claude-3-sonnet-20240229",
        max_tokens: int | None = None,
        temperature: float = 0.7,
        correlation_id: str = "unknown",
        **kwargs: Any,
    ) -> str:
        """Generate text using Anthropic API."""
        return await self._make_request(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            correlation_id=correlation_id,
            **kwargs,
        )

    async def _internal_generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        correlation_id: str,
        max_tokens: int | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Internal Anthropic API call."""
        if not self.api_key:
            raise LLMError(
                message="Anthropic API key not configured",
                agent_type="anthropic_client",
                correlation_id=correlation_id,
            )

        # Convert messages to Anthropic format
        system_message = None
        anthropic_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append(msg)

        payload = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens or 4000,
            "temperature": temperature,
        }

        if system_message:
            payload["system"] = system_message

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        try:
            async with httpx.AsyncClient(timeout=self.request_timeout_s) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()

                if "content" not in data or not data["content"]:
                    raise LLMError(
                        message="No content in Anthropic response",
                        agent_type="anthropic_client",
                        correlation_id=correlation_id,
                        details={"response": data},
                    )

                content = data["content"][0]["text"]
                self.logger.info(
                    "Anthropic API call successful",
                    model=model,
                    correlation_id=correlation_id,
                    tokens_used=data.get("usage", {}).get("output_tokens", 0),
                )

                return content

        except httpx.HTTPStatusError as e:
            truncated = (e.response.text or "")[:512]
            self.logger.exception(
                "Anthropic API HTTP error",
                status_code=e.response.status_code,
                response_text_truncated=truncated,
                correlation_id=correlation_id,
            )
            raise LLMError(
                message=f"Anthropic API HTTP error: {e.response.status_code}",
                agent_type="anthropic_client",
                correlation_id=correlation_id,
                details={
                    "status_code": e.response.status_code,
                    "response_truncated": truncated,
                },
            ) from e
        except httpx.RequestError as e:
            self.logger.exception(
                "Anthropic API request error",
                correlation_id=correlation_id,
            )
            raise LLMError(
                message=f"Anthropic API request failed: {e!s}",
                agent_type="anthropic_client",
                correlation_id=correlation_id,
                details={"error": str(e)},
            ) from e


class LLMManager:
    """Manages multiple LLM providers with failover."""

    def __init__(self) -> None:
        self.clients: dict[LLMProvider, LLMClient] = {}
        self.default_provider = LLMProvider.OPENAI
        self.logger = get_logger("llm_manager")

    async def initialize(self) -> None:
        """Initialize LLM clients with API keys from Vault."""
        vault_settings = get_vault_settings()

        # Initialize OpenAI client
        openai_key = await vault_settings.get_openai_api_key()
        if openai_key:
            self.clients[LLMProvider.OPENAI] = OpenAIClient(api_key=openai_key)
            self.logger.info("OpenAI client initialized")

        # Initialize Anthropic client
        anthropic_key = await vault_settings.get_anthropic_api_key()
        if anthropic_key:
            self.clients[LLMProvider.ANTHROPIC] = AnthropicClient(api_key=anthropic_key)
            self.logger.info("Anthropic client initialized")

        if not self.clients:
            self.logger.warning("No LLM clients initialized - check API keys in Vault")

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        provider: LLMProvider | None = None,
        correlation_id: str = "unknown",
        **kwargs: Any,
    ) -> str:
        """Generate text with provider fallback."""
        provider = provider or self.default_provider

        # Try primary provider first
        if provider in self.clients:
            try:
                return await self.clients[provider].generate(
                    messages=messages,
                    model=model or self._get_default_model(provider),
                    correlation_id=correlation_id,
                    **kwargs,
                )
            except LLMError as exc:
                self.logger.warning(
                    "Primary LLM provider failed",
                    provider=provider,
                    error=str(exc),
                    correlation_id=correlation_id,
                )

        # Try fallback providers
        for fallback_provider, client in self.clients.items():
            if fallback_provider != provider:
                try:
                    self.logger.info(
                        "Trying fallback LLM provider",
                        provider=fallback_provider,
                        correlation_id=correlation_id,
                    )
                    return await client.generate(
                        messages=messages,
                        model=model or self._get_default_model(fallback_provider),
                        correlation_id=correlation_id,
                        **kwargs,
                    )
                except LLMError as exc:
                    self.logger.warning(
                        "Fallback LLM provider failed",
                        provider=fallback_provider,
                        error=str(exc),
                        correlation_id=correlation_id,
                    )

        raise LLMError(
            message="All LLM providers failed",
            agent_type="llm_manager",
            correlation_id=correlation_id,
            details={"attempted_providers": list(self.clients.keys())},
        )

    def _get_default_model(self, provider: LLMProvider) -> str:
        """Get default model for provider."""
        if provider == LLMProvider.OPENAI:
            # Try environment variable, then fallback to current recommended models
            return (
                os.getenv("OPENAI_DEFAULT_MODEL") or "gpt-4o"  # Legacy fallback
            )
        elif provider == LLMProvider.ANTHROPIC:
            # Try environment variable, then fallback to current recommended models
            return (
                os.getenv("ANTHROPIC_DEFAULT_MODEL")
                or "claude-sonnet-4"  # Legacy fallback
            )
        else:
            return "gpt-4"  # Default fallback


# Global LLM manager instance
llm_manager = LLMManager()
