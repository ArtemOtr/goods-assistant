import logging
from typing import TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from src.settings import settings

logger = logging.getLogger(__name__)
SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMConfigurationError(RuntimeError):
    pass


class LLMClient:
    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if not settings.llm.api_key:
            raise LLMConfigurationError(
                "LLM API key is not configured. Set the environment variable referenced by "
                "llm.api_key or place the key directly in config.yaml."
            )
        if self._client is None:
            self._client = AsyncOpenAI(
                base_url=settings.llm.base_url,
                api_key=settings.llm.api_key,
                timeout=settings.llm.timeout,
                max_retries=settings.llm.max_retries,
            )
        return self._client

    async def generate_structured(
        self,
        *,
        messages: list[dict[str, str]],
        schema: type[SchemaT],
    ) -> SchemaT:
        model = settings.llm.model
        logger.info("Structured LLM request started: model=%s", model)
        response = await self._get_client().chat.completions.create(
            model=model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            },
            temperature=settings.llm.temperature,
            max_tokens=settings.llm.max_tokens,
            extra_body={
                "reasoning": {
                    "enabled": settings.llm.reasoning_enabled,
                }
            },
        )
        if not response.choices:
            raise ValueError("LLM returned no choices")

        message = response.choices[0].message
        if message.refusal:
            raise ValueError(f"LLM refused the request: {message.refusal}")
        if not message.content:
            raise ValueError("LLM returned empty content")

        logger.info("Structured LLM request completed: model=%s", response.model)
        return schema.model_validate_json(message.content)

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.close()


llm_client = LLMClient()
