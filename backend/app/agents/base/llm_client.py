"""
LLM client with retry logic and circuit breakers.
Supports multiple LLM providers with failover.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum
import time

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from app.core.logger import get_logger
from app.core.config import get_vault_settings
from ..contracts.base import LLMError

logger = get_logger()


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
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED

    async def call(self, func, *args, **kwargs):
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

    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    def __init__(self, provider: LLMProvider, circuit_breaker: Optional[CircuitBreaker] = None):
        self.provider = provider
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.logger = get_logger(f"llm.{provider}")

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Generate text completion."""
        pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=16),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        before_sleep=before_sleep_log(logger, "WARNING"),
    )
    async def _make_request(
        self,
        messages: List[Dict[str, str]],
        model: str,
        correlation_id: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs,
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
        messages: List[Dict[str, str]],
        model: str,
        correlation_id: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Internal implementation of text generation."""
        pass


class OpenAIClient(LLMClient):
    """OpenAI API client with retry and circuit breaker."""

    def __init__(self, api_key: Optional[str] = None, circuit_breaker: Optional[CircuitBreaker] = None):
        super().__init__(LLMProvider.OPENAI, circuit_breaker)
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        correlation_id: str = "unknown",
        **kwargs,
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
        messages: List[Dict[str, str]],
        model: str,
        correlation_id: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs,
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
            async with httpx.AsyncClient(timeout=30.0) as client:
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
            self.logger.error(
                "OpenAI API HTTP error",
                status_code=e.response.status_code,
                response_text=e.response.text,
                correlation_id=correlation_id,
            )
            raise LLMError(
                message=f"OpenAI API HTTP error: {e.response.status_code}",
                agent_type="openai_client",
                correlation_id=correlation_id,
                details={"status_code": e.response.status_code, "response": e.response.text},
            )
        except httpx.RequestError as e:
            self.logger.error(
                "OpenAI API request error",
                error=str(e),
                correlation_id=correlation_id,
            )
            raise LLMError(
                message=f"OpenAI API request failed: {str(e)}",
                agent_type="openai_client",
                correlation_id=correlation_id,
                details={"error": str(e)},
            )


class AnthropicClient(LLMClient):
    """Anthropic/Claude API client with retry and circuit breaker."""

    def __init__(self, api_key: Optional[str] = None, circuit_breaker: Optional[CircuitBreaker] = None):
        super().__init__(LLMProvider.ANTHROPIC, circuit_breaker)
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1"

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-3-sonnet-20240229",
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        correlation_id: str = "unknown",
        **kwargs,
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
        messages: List[Dict[str, str]],
        model: str,
        correlation_id: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs,
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
            async with httpx.AsyncClient(timeout=30.0) as client:
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
            self.logger.error(
                "Anthropic API HTTP error",
                status_code=e.response.status_code,
                response_text=e.response.text,
                correlation_id=correlation_id,
            )
            raise LLMError(
                message=f"Anthropic API HTTP error: {e.response.status_code}",
                agent_type="anthropic_client",
                correlation_id=correlation_id,
                details={"status_code": e.response.status_code, "response": e.response.text},
            )
        except httpx.RequestError as e:
            self.logger.error(
                "Anthropic API request error",
                error=str(e),
                correlation_id=correlation_id,
            )
            raise LLMError(
                message=f"Anthropic API request failed: {str(e)}",
                agent_type="anthropic_client",
                correlation_id=correlation_id,
                details={"error": str(e)},
            )


class LLMManager:
    """Manages multiple LLM providers with failover."""

    def __init__(self):
        self.clients: Dict[LLMProvider, LLMClient] = {}
        self.default_provider = LLMProvider.OPENAI
        self.logger = get_logger("llm_manager")

    async def initialize(self):
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
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        provider: Optional[LLMProvider] = None,
        correlation_id: str = "unknown",
        **kwargs,
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
            except LLMError as e:
                self.logger.warning(
                    f"Primary LLM provider {provider} failed",
                    error=str(e),
                    correlation_id=correlation_id,
                )

        # Try fallback providers
        for fallback_provider, client in self.clients.items():
            if fallback_provider != provider:
                try:
                    self.logger.info(
                        f"Trying fallback LLM provider {fallback_provider}",
                        correlation_id=correlation_id,
                    )
                    return await client.generate(
                        messages=messages,
                        model=model or self._get_default_model(fallback_provider),
                        correlation_id=correlation_id,
                        **kwargs,
                    )
                except LLMError as e:
                    self.logger.warning(
                        f"Fallback LLM provider {fallback_provider} failed",
                        error=str(e),
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
        defaults = {
            LLMProvider.OPENAI: "gpt-4",
            LLMProvider.ANTHROPIC: "claude-3-sonnet-20240229",
        }
        return defaults.get(provider, "gpt-4")


# Global LLM manager instance
llm_manager = LLMManager()