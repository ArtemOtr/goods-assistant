# Goods AI Assistant

MVP-сервис на FastAPI, который получает проверенные данные о контрольно-измерительном
приборе и формирует редакционную часть товарной карточки.

LLM создаёт только SEO-заголовок, описание, поисковые запросы и коммерческий блок.
Название, производитель и характеристики попадают в результат напрямую из входного JSON.

## Архитектура

```text
POST /v1/product-cards/generate
              │
              ▼
     FastAPI router
              │
              ▼
     ProductCardService
       ├── проверка исходных данных
       ├── перенос specs без LLM
       ├── генерация текстов через LLMClient
       └── проверка новых числовых значений
              │
              ▼
       итоговый ProductCard
```

Сервис возвращает готовую карточку одним JSON-ответом.

## Запуск

Требуются Python 3.12+ и `uv`.

```bash
cp src/config.example.yaml src/config.yaml

# Затем укажите OPENROUTER_API_KEY или вставьте ключ в llm.api_key файла src/config.yaml.
export OPENROUTER_API_KEY="sk-or-v1-..."

uv sync
uv run uvicorn src.main:create_app --factory --reload
```

Шаблон уже настроен на бесплатную модель `google/gemma-4-31b-it:free`.
Созданный локальный `src/config.yaml` исключён из Git. Вместо переменной окружения ключ
можно записать непосредственно в поле `llm.api_key` этого файла:

```yaml
llm:
  api_key: "sk-or-v1-..."
```

Для генерации карточки внутреннее рассуждение модели отключено, чтобы оно не расходовало
лимит ответа перед формированием JSON:

```yaml
llm:
  reasoning_enabled: false
```

Конфигурационный файл можно разместить в другом месте:

```bash
export GOODS_AI_CONFIG=/absolute/path/to/config.yaml
```

Swagger UI: <http://localhost:8000/docs>

Healthcheck: <http://localhost:8000/health>

## Обычный запрос

```bash
curl -X POST http://localhost:8000/v1/product-cards/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Манометр показывающий DM 02",
    "manufacturer": "Манотомь",
    "specs": {
      "диапазон измерений": "0–1,6 МПа",
      "класс точности": "1,5",
      "присоединение": "G1/2",
      "диаметр корпуса": "100 мм"
    },
    "description": "Прибор предназначен для измерения избыточного давления."
  }'
```

## Примеры

Сохранённые примеры результатов подготовлены с фиксированной бесплатной моделью
`nvidia/nemotron-3.5-super-vl:free` через OpenRouter. Модель в конфигурации заменяема;
в текущем `config.example.yaml` для запуска указана `google/gemma-4-31b-it:free`, поэтому
формулировки нового ответа могут отличаться при сохранении той же JSON-схемы.

В каталоге [`examples`](examples/) находятся пары входных данных и готовых ответов:

- манометр из тестового задания: [`input`](examples/pdf_manometer.input.json) и
  [`output`](examples/pdf_manometer.output.json);
- расширенный пример преобразователя сигнала: [`input`](examples/signal_converter.input.json)
  и [`output`](examples/signal_converter.output.json);
- расширенный пример датчика давления: [`input`](examples/verified_standard.input.json) и
  [`output`](examples/verified_standard.output.json);
- товар с неполными данными: [`input`](examples/sparse_thermometer.input.json) и
  [`output`](examples/sparse_thermometer.output.json).

## Конфигурация

Все параметры LLM и промпты находятся в `src/config.yaml`. Этот файл исключён из Git.
Безопасный шаблон хранится в `src/config.example.yaml`. Значение ключа можно записать
непосредственно в локальный конфиг либо подставить через `${OPENROUTER_API_KEY}`.

## Защита от выдуманных характеристик

- `characteristics` строятся программно из `specs`, без участия LLM;
- структурированный ответ LLM проверяется Pydantic;
- длина заголовка, описания и количество запросов проверяются схемой;
- числа в сгенерированном тексте сравниваются с числами во входных данных;
- при ошибке проверки фактов модель получает причину и один раз перегенерирует ответ;
- отсутствующие поля определяются кодом и возвращаются в `quality.missing_data`.
