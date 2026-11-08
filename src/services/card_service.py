import json
import logging
import re

from src.schemas.product_card import (
    Characteristic,
    GeneratedContent,
    ProductCard,
    ProductCardRequest,
    QualityReport,
)
from src.services.llm_client import LLMClient
from src.settings import settings

_NUMBER_PATTERN = re.compile(r"(?<![\w])\d+(?:[.,]\d+)?(?![\w])", re.UNICODE)
logger = logging.getLogger(__name__)


class UnsupportedGeneratedFactsError(ValueError):
    pass


class ProductCardService:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def generate(self, product: ProductCardRequest) -> ProductCard:
        characteristics, quality = self._prepare_source_data(product)
        product_json = json.dumps(product.model_dump(), ensure_ascii=False, indent=2)
        messages = [
            {"role": "system", "content": settings.prompts.system},
            {
                "role": "user",
                "content": settings.prompts.user.format(product_json=product_json),
            },
        ]

        for attempt in range(settings.generation.fact_validation_retries + 1):
            generated = await self._llm_client.generate_structured(
                messages=messages,
                schema=GeneratedContent,
            )
            try:
                self._validate_generated_numbers(product, generated)
                break
            except UnsupportedGeneratedFactsError as exc:
                if attempt == settings.generation.fact_validation_retries:
                    raise

                logger.warning("Generated content contains unsupported numbers; retrying: %s", exc)
                messages.extend(
                    [
                        {"role": "assistant", "content": generated.model_dump_json()},
                        {
                            "role": "user",
                            "content": settings.prompts.correction.format(
                                validation_error=str(exc),
                            ),
                        },
                    ]
                )

        return ProductCard(
            name=product.name,
            manufacturer=product.manufacturer,
            characteristics=characteristics,
            generated=generated,
            quality=quality,
        )

    @staticmethod
    def _prepare_source_data(
        product: ProductCardRequest,
    ) -> tuple[list[Characteristic], QualityReport]:
        characteristics: list[Characteristic] = []
        missing_data: list[str] = []
        warnings: list[str] = []
        seen_names: set[str] = set()

        if product.manufacturer is None:
            missing_data.append("Не указан производитель")
        if product.description is None:
            missing_data.append("Отсутствует исходное описание товара")
        if not product.specs:
            missing_data.append("Не указаны технические характеристики")

        for raw_name, raw_value in product.specs.items():
            name = raw_name.strip()
            if not name:
                warnings.append("Обнаружена характеристика без названия")
                continue
            if name.casefold() in seen_names:
                warnings.append(f"Характеристика «{name}» указана повторно")
            seen_names.add(name.casefold())

            if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
                missing_data.append(f"Не указано значение характеристики «{name}»")
                continue
            characteristics.append(Characteristic(name=name, value=str(raw_value).strip()))

        return characteristics, QualityReport(missing_data=missing_data, warnings=warnings)

    @staticmethod
    def _validate_generated_numbers(
        product: ProductCardRequest,
        generated: GeneratedContent,
    ) -> None:
        if not settings.generation.reject_unsupported_numbers:
            return

        def extract_numbers(text: str) -> set[str]:
            return {
                value.replace(",", ".").lstrip("0") or "0"
                for value in _NUMBER_PATTERN.findall(text)
            }

        source_numbers = extract_numbers(json.dumps(product.model_dump(), ensure_ascii=False))
        generated_fields = {
            "seo_title": [generated.seo_title],
            "seo_description": [generated.seo_description],
            "search_queries": generated.search_queries,
            "commercial_block": [generated.commercial_block],
        }
        unsupported_by_field = {
            field_name: sorted(
                {
                    number
                    for field_value in field_values
                    for number in extract_numbers(field_value)
                }
                - source_numbers
            )
            for field_name, field_values in generated_fields.items()
        }
        unsupported_by_field = {
            field_name: values for field_name, values in unsupported_by_field.items() if values
        }
        if unsupported_by_field:
            details = "; ".join(
                f"{field_name}: {', '.join(values)}" for field_name, values in unsupported_by_field.items()
            )
            raise UnsupportedGeneratedFactsError(
                "LLM added numeric values absent from the source: " + details
            )
