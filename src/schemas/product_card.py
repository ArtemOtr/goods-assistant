from pydantic import BaseModel, ConfigDict, Field, field_validator

type SpecValue = str | int | float | bool | None


class ProductCardRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, description="Название товара")
    manufacturer: str | None = Field(default=None, description="Производитель")
    specs: dict[str, SpecValue] = Field(default_factory=dict)
    description: str | None = Field(default=None, description="Фрагмент паспорта или исходное описание")

    @field_validator("manufacturer", "description", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class Characteristic(BaseModel):
    name: str
    value: str


class GeneratedContent(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    seo_title: str = Field(
        min_length=1,
        max_length=70,
        description="Законченный SEO-заголовок без обрыва слова и без неподтверждённых фактов.",
    )
    seo_description: str = Field(
        min_length=800,
        max_length=1200,
        description="SEO-описание только по входным фактам, без догадок и новых применений.",
    )
    search_queries: list[str] = Field(
        min_length=3,
        max_length=5,
        description="Запросы только на основе названия, производителя, назначения и точных характеристик.",
    )
    commercial_block: str = Field(
        min_length=1,
        description="Подтверждённая входными данными задача прибора без придуманной аудитории.",
    )

    @field_validator("search_queries")
    @classmethod
    def validate_search_queries(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        if len(normalized) != len(values):
            raise ValueError("search queries must not be empty")
        if len({value.casefold() for value in normalized}) != len(normalized):
            raise ValueError("search queries must be unique")
        return normalized


class QualityReport(BaseModel):
    missing_data: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ProductCard(BaseModel):
    name: str
    manufacturer: str | None
    characteristics: list[Characteristic]
    generated: GeneratedContent
    quality: QualityReport
