import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"
EXAMPLE_CONFIG_PATH = Path(__file__).resolve().parent / "config.example.yaml"
_ENV_PATTERN = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")
_DEFAULT_CORRECTION_PROMPT = (
    "Предыдущий ответ отклонён проверкой фактов: {validation_error}. "
    "Сформируй весь ответ заново. Используй только числа и технические значения "
    "из исходных данных. Не объясняй исправления."
)


class AppSettings(BaseModel):
    name: str = "goods-ai-assistant"
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    debug: bool = False
    log_level: str = "INFO"


class LLMSettings(BaseModel):
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    timeout: float = Field(default=60.0, gt=0)
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=2500, gt=0)
    max_retries: int = Field(default=2, ge=0)
    reasoning_enabled: bool = False


class PromptSettings(BaseModel):
    system: str
    user: str
    correction: str = _DEFAULT_CORRECTION_PROMPT


class GenerationSettings(BaseModel):
    reject_unsupported_numbers: bool = True
    fact_validation_retries: int = Field(default=1, ge=0, le=3)


class Settings(BaseModel):
    app: AppSettings = Field(default_factory=AppSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    prompts: PromptSettings
    generation: GenerationSettings = Field(default_factory=GenerationSettings)

    @classmethod
    def from_yaml(cls, path: Path) -> "Settings":
        raw_text = path.read_text(encoding="utf-8")
        expanded_text = _ENV_PATTERN.sub(
            lambda match: os.getenv(match.group(1), ""),
            raw_text,
        )
        payload: dict[str, Any] = yaml.safe_load(expanded_text) or {}
        return cls.model_validate(payload)


def _config_path() -> Path:
    configured_path = os.getenv("GOODS_AI_CONFIG")
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    if DEFAULT_CONFIG_PATH.exists():
        return DEFAULT_CONFIG_PATH
    return EXAMPLE_CONFIG_PATH


@lru_cache
def get_settings() -> Settings:
    return Settings.from_yaml(_config_path())


settings = get_settings()
