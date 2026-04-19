from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from groq import APIError, APIStatusError, Groq

log = logging.getLogger(__name__)


@dataclass
class CompletionResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str
    latency_s: float


class LLMClient:
    """Groq-backed completion client with simple exponential backoff.

    Kept intentionally thin: no streaming, no tool calls, no prompt templating.
    The goal is a stable surface the rest of the codebase can trust, not a
    re-implementation of LangChain.
    """

    def __init__(self, api_key: str, model: str, max_retries: int = 3):
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY not set. Copy .env.example to .env and add your free key from https://console.groq.com"
            )
        self._client = Groq(api_key=api_key)
        self._model = model
        self._max_retries = max_retries

    @property
    def model(self) -> str:
        return self._model

    def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> CompletionResult:
        attempt = 0
        while True:
            attempt += 1
            started = time.monotonic()
            kwargs: dict = {
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            try:
                resp = self._client.chat.completions.create(**kwargs)
            except APIStatusError as e:
                if attempt > self._max_retries or e.status_code not in {429, 500, 502, 503}:
                    raise
                backoff = min(2**attempt, 30)
                log.warning(
                    "Groq returned %s on attempt %d/%d; sleeping %ds",
                    e.status_code,
                    attempt,
                    self._max_retries,
                    backoff,
                )
                time.sleep(backoff)
                continue
            except APIError:
                if attempt > self._max_retries:
                    raise
                time.sleep(min(2**attempt, 30))
                continue

            latency = time.monotonic() - started
            choice = resp.choices[0]
            usage = resp.usage
            return CompletionResult(
                text=choice.message.content or "",
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                model=self._model,
                latency_s=latency,
            )
