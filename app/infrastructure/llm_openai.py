from typing import List, Dict, Optional, Iterator
from openai import OpenAI

from app.infrastructure.llm_errors import execute_with_retry_and_fallback
from app.domain.ports import LlmPort, LlmResult
from app.core.config import settings

class OpenAiCompatibleLlmAdapter(LlmPort):
    def __init__(self):
        self.base_url = settings.LLM_BASE_URL.strip()
        self.api_key = settings.LLM_API_KEY.strip()
        self.model = settings.MAIN_MODEL.strip()
        self.fallback_model = (settings.MAIN_MODEL_FALLBACK or "").strip() or None
        self.max_retries = settings.LLM_MAX_RETRIES
        self._client = None

        if self.is_configured():
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
            )

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    def generate_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str] = None) -> LlmResult:
        if not self._client:
            raise RuntimeError("Klient LLM nie jest skonfigurowany.")

        full_messages = [{"role": "system", "content": system_prompt}] + messages
        target_primary = model_override or self.model

        def _call(chosen_model: Optional[str]) -> LlmResult:
            active_model = chosen_model or target_primary
            response = self._client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            choice = response.choices[0].message.content or "{}"
            usage = response.usage
            tokens_used = usage.total_tokens if usage else 0

            return LlmResult(
                raw_content=choice,
                tokens_used=tokens_used,
                model=response.model or self.model,
                debug_info={
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                },
            )
        return execute_with_retry_and_fallback(
            fn=_call,
            primary_model=target_primary,
            fallback_model=self.fallback_model,
            max_retries=self.max_retries,
        )

    def stream_json(
            self,
            system_prompt: str,
            messages: List[Dict[str, str]],
            model_override: Optional[str] = None,
    ) -> Iterator[str]:
        if not self._client:
            raise RuntimeError("Klient LLM nie jest skonfigurowany.")

        full_messages = [{"role": "system", "content": system_prompt}] + messages
        target_primary = model_override or self.model

        def _open_stream(chosen_model: Optional[str]):
            active_model = chosen_model or target_primary
            return self._client.chat.completions.create(
                model=active_model,
                messages=full_messages,
                temperature=0.2,
                response_format={"type": "json_object"},
                stream=True,
            )

        stream = execute_with_retry_and_fallback(
            fn=_open_stream,
            primary_model=target_primary,
            fallback_model=self.fallback_model,
            max_retries=self.max_retries,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content