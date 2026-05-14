# API Template — Шаблон для создания API-обёртки

## Описание

Этот шаблон предоставляет **унифицированную структуру API** для обёртки вокруг проектов студентов.

**Архитектура:**

- Вы реализуете свою логику в `app/service.py`.
- Остальная инфраструктура (FastAPI, схемы, Docker) остаётся без изменений.
- Контейнер слушает порт **8000** и реализует три эндпоинта: `/health`, `/info`, `/run`.
- Нагрузочный тест (Locust) автоматически определяет тип входных данных через `/info` и генерирует подходящие запросы.

Все сервисы получают запросы в **одинаковом формате**. Поле `content` может быть строкой (текст) или списком типизированных частей (текст + картинка). Дополнительные параметры передаются в `extra_body`.

---

## Быстрый старт

### Запуск через Docker Compose

```bash
docker compose up --build
```

### Проверка работоспособности

```bash
# Health check
curl http://localhost:8000/health
# → {"status": "ok"}

# Информация о сервисе
curl http://localhost:8000/info

# Текстовый запрос
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Привет, мир!"
  }'

# Мультимодальный запрос (текст + картинка)
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "content": [
      {"type": "text", "text": "Что на этой картинке?"},
      {"type": "image", "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="}
    ],
    "extra_body": {"echo_prefix": "Эхо: "}
  }'
```
---

## Формат запроса

### Общая структура

Все запросы к `/run` имеют **одинаковую структуру**:

```json
{
  "content": "...",
  "extra_body": {}
}
```

- `content` — основной ввод. Может быть **строкой** или **списком**.
- `extra_body` — необязательный словарь с параметрами (температура, max_tokens, и т.д.). По умолчанию `{}`.

### Текстовый запрос (content — строка)

Если `content` — строка, это **всегда текст**. Самый простой вариант:

```json
{
  "content": "Привет, мир!"
}
```

С параметрами:

```json
{
  "content": "Напиши стихотворение про кота",
  "extra_body": {
    "temperature": 0.7,
    "max_tokens": 512
  }
}
```

### Запрос с картинкой (content — список)

Для передачи картинки используется список с одной частью `type: "image"`:

```json
{
  "content": [
    {"type": "image", "image": "<base64-кодированная картинка>"}
  ]
}
```

### Мультимодальный запрос (текст + картинка)

Для одновременной передачи текста и картинки:

```json
{
  "content": [
    {"type": "text", "text": "Что изображено на этой картинке?"},
    {"type": "image", "image": "<base64-кодированная картинка>"}
  ],
  "extra_body": {
    "temperature": 0.5
  }
}
```

### extra_body — дополнительные параметры

Поле `extra_body` — это словарь с **сервис-specific параметрами**. Каждый сервис определяет свои параметры самостоятельно.

Примеры:

```json
{"extra_body": {"temperature": 0.7, "max_tokens": 1024}}
{"extra_body": {"model": "gpt-oss-120b", "top_p": 0.9}}
{"extra_body": {}}
```

---

## Как написать свой сервис

Вам нужно изменить `app/service.py`.

### Шаг 1: Создайте класс-наследник `ServiceBase`

Откройте `app/service.py` и добавьте свой класс:

```python
class MyService(ServiceBase):
    def get_info(self) -> InfoResponse:
        return InfoResponse(
            input_type=InputType.TEXT,
            input_schema=Schema.of(),
            output_schema=Schema.of(),
        )

    def run(self, request: RunRequest) -> RunResponse:
        ...
```

### Шаг 2: Реализуйте `get_info()`

Этот метод возвращает метаданные сервиса. Используйте конструктор `Schema` для построения JSON-схем:

```python
def get_info(self) -> InfoResponse:
    return InfoResponse(
        input_type=InputType.TEXT,
        input_schema=Schema.of(
            temperature=Schema.number("Температура генерации", default=0.7),
            max_tokens=Schema.integer("Максимум токенов", default=512),
        ),
        output_schema=Schema.of(
            answer=Schema.string("Ответ модели"),
            tokens_used=Schema.integer("Использовано токенов"),
        ),
    )
```

**Выбор `input_type`:**

| `input_type` | Что отправляет нагрузочный тест | Когда использовать |
|---|---|---|
| `"text"` | `{"content": "текст"}` | Ваш сервис работает только с текстом (LLM) |
| `"image"` | `{"content": [{"type": "image", ...}]}` | Ваш сервис работает только с картинками |
| `"text_and_image"` | `{"content": [{"type": "text", ...}, {"type": "image", ...}]}` | Ваш сервис принимает текст + картинку |

### Шаг 3: Реализуйте `run()`

Этот метод содержит основную логику:

```python
def run(self, request: RunRequest) -> RunResponse:
    try:
        # Извлекаем текст (вернёт None, если текста нет)
        text = self.get_text(request)

        # Извлекаем картинку base64 (вернёт None, если картинки нет)
        image_b64 = self.get_image(request)

        # Читаем параметры из extra_body
        temperature = request.extra_body.get("temperature", 0.7)

        # Ваша логика обработки...
        result = {"answer": "Результат работы", "tokens_used": 42}

        return RunResponse(status="success", result=result)
    except Exception as exc:
        return RunResponse(status="error", error=str(exc))
```

### Шаг 4: Обновите `get_service()`

В конце файла `app/service.py` замените `DemoService` на ваш класс:

```python
def get_service() -> ServiceBase:
    global _service_instance
    if _service_instance is None:
        _service_instance = MyService()  # <-- Ваш класс
    return _service_instance
```

---

## Helper-методы ServiceBase

`ServiceBase` предоставляет два helper-метода для извлечения данных из запроса:

### `self.get_text(request) -> str | None`

Извлекает текст из `content`:
- Если `content` — строка → возвращает её как есть.
- Если `content` — список → ищет первую часть с `type="text"` и возвращает её текст.
- Если текст не найден → возвращает `None`.

```python
text = self.get_text(request)
if text is None:
    return RunResponse(status="error", error="Текст не передан")
```

### `self.get_image(request) -> str | None`

Извлекает base64-кодированную картинку из `content`:
- Если `content` — список → ищет первую часть с `type="image"` и возвращает base64-строку.
- Если `content` — строка или картинка не найдена → возвращает `None`.

```python
image_b64 = self.get_image(request)
if image_b64 is None:
    return RunResponse(status="error", error="Картинка не передана")
image_bytes = base64.b64decode(image_b64)
```

---

## Конструктор Schema

Класс `Schema` из `app.schemas` — удобный builder для JSON Schema вместо ручного написания словарей.

### Сравнение

**Без Schema (было):**
```python
input_schema={
    "type": "object",
    "properties": {
        "temperature": {
            "type": "number",
            "description": "Температура генерации.",
            "default": 0.7,
        },
    },
}
```

**Со Schema (стало):**
```python
input_schema=Schema.of(
    temperature=Schema.number("Температура генерации", default=0.7),
)
```

### Методы

| Метод | Описание |
|---|---|
| `Schema.of(name=field, ...)` | Объект со свойствами (корневой уровень схемы) |
| `Schema.string(desc, default=..., enum=...)` | Строка |
| `Schema.number(desc, default=..., minimum=..., maximum=...)` | Число (float) |
| `Schema.integer(desc, default=..., minimum=..., maximum=...)` | Целое число |
| `Schema.boolean(desc, default=...)` | Логическое значение |
| `Schema.array(items, desc)` | Массив, `items` — схема элемента |
| `Schema.object(desc, name=field, ...)` | Вложенный объект |

### Примеры

```python
# Простые поля
Schema.string("Описание поля", default="привет")
Schema.number("Температура", default=0.7, minimum=0.0, maximum=2.0)
Schema.integer("Максимум токенов", default=512)
Schema.boolean("Стриминг", default=False)

# Массив объектов
Schema.array(
    Schema.object(label=Schema.string(), confidence=Schema.number()),
    "Список классов",
)

# Пустая схема (если нет параметров)
Schema.of()
```

---

## Полные примеры

### Пример 1: LLM текстовый сервис (суммаризация)

Полный рабочий код для сервиса суммаризации текста:

```python
import base64
import io
from typing import Any

from app.schemas import (
    InfoResponse,
    InputType,
    RunRequest,
    RunResponse,
    Schema,
)
from app.service import ServiceBase


class LLMSummarizerService(ServiceBase):
    """Сервис суммаризации текста с помощью LLM."""

    def get_info(self) -> InfoResponse:
        return InfoResponse(
            input_type=InputType.TEXT,
            input_schema=Schema.of(
                max_length=Schema.integer("Макс. длина саммари (в словах)", default=50),
            ),
            output_schema=Schema.of(
                summary=Schema.string("Суммаризованный текст"),
                original_length=Schema.integer("Длина исходного текста"),
                summary_length=Schema.integer("Длина саммари"),
            ),
        )

    def run(self, request: RunRequest) -> RunResponse:
        try:
            text = self.get_text(request)
            if text is None:
                return RunResponse(
                    status="error",
                    error="Текст не передан. Отправьте content как строку.",
                )

            max_length = request.extra_body.get("max_length", 50)

            # Здесь вызов вашего сервиса из проекта
            # Ниже — заглушка для демонстрации
            summary = src.your_app.run(text, max_length)

            return RunResponse(
                status="success",
                result={
                    "summary": summary,
                    "original_length": len(text),
                    "summary_length": len(summary),
                },
            )
        except Exception as exc:
            return RunResponse(status="error", error=str(exc))


# Не забудьте обновить get_service():
# _service_instance = LLMSummarizerService()
```

### Пример 2: VLM сервис (классификация картинок)

Полный рабочий код для сервиса классификации изображений:

```python
import base64
import io
from typing import Any

from app.schemas import (
    InfoResponse,
    InputType,
    RunRequest,
    RunResponse,
    Schema,
)
from app.service import ServiceBase


class ImageClassifierService(ServiceBase):
    """Сервис классификации изображений."""

    def get_info(self) -> InfoResponse:
        return InfoResponse(
            input_type=InputType.IMAGE,
            input_schema=Schema.of(
                top_k=Schema.integer("Количество возвращаемых классов", default=3),
            ),
            output_schema=Schema.of(
                classes=Schema.array(
                    Schema.object(
                        label=Schema.string("Название класса"),
                        confidence=Schema.number("Уверенность (0.0 — 1.0)"),
                    ),
                    "Список классов",
                ),
                image_size=Schema.object(
                    "Размеры картинки",
                    width=Schema.integer("Ширина"),
                    height=Schema.integer("Высота"),
                ),
            ),
        )

    def run(self, request: RunRequest) -> RunResponse:
        try:
            image_b64 = self.get_image(request)
            if image_b64 is None:
                return RunResponse(
                    status="error",
                    error="Картинка не передана. Используйте content: [{type: image, image: ...}].",
                )

            top_k = request.extra_body.get("top_k", 3)

            # Декодируем картинку
            image_bytes = base64.b64decode(image_b64)

            # Получаем размеры через Pillow
            from PIL import Image
            img = Image.open(io.BytesIO(image_bytes))

            # Здесь вызов вашего сервиса из проекта
            # Ниже — заглушка для демонстрации
            classes = src.your_app.run(img, top_k)

            return RunResponse(
                status="success",
                result={
                    "classes": classes,
                    "image_size": {"width": img.width, "height": img.height},
                },
            )
        except Exception as exc:
            return RunResponse(status="error", error=str(exc))


# Не забудьте обновить get_service():
# _service_instance = ImageClassifierService()
```

### Пример 3: Текстовый сервис с extra_body (температура, max_tokens)

Полный рабочий код текстового сервиса с несколькими параметрами:

```python
from typing import Any

from app.schemas import (
    InfoResponse,
    InputType,
    RunRequest,
    RunResponse,
    Schema,
)
from app.service import ServiceBase


class TextGeneratorService(ServiceBase):
    """Генерация текста с настраиваемыми параметрами."""

    def get_info(self) -> InfoResponse:
        return InfoResponse(
            input_type=InputType.TEXT,
            input_schema=Schema.of(
                temperature=Schema.number("Температура генерации (0.0 — 2.0)", default=0.7, minimum=0.0, maximum=2.0),
                max_tokens=Schema.integer("Максимум токенов", default=512),
                top_p=Schema.number("Top-p (nucleus) sampling", default=0.9),
            ),
            output_schema=Schema.of(
                generated_text=Schema.string("Сгенерированный текст"),
                tokens_used=Schema.integer("Использовано токенов"),
                model=Schema.string("Использованная модель"),
            ),
        )

    def run(self, request: RunRequest) -> RunResponse:
        try:
            text = self.get_text(request)
            if text is None:
                return RunResponse(status="error", error="Текст не передан.")

            # Читаем все параметры из extra_body с значениями по умолчанию
            temperature = request.extra_body.get("temperature", 0.7)
            max_tokens = request.extra_body.get("max_tokens", 512)
            top_p = request.extra_body.get("top_p", 0.9)
            stop = request.extra_body.get("stop", [])

            # Здесь вызов вашего сервиса из проекта
            generated = src.your_app.run(text, temperature, max_tokents, top_p, stop)

            return RunResponse(
                status="success",
                result={
                    "generated_text": generated,
                    "tokens_used": len(generated.split()),
                    "model": "demo-model-v1",
                },
            )
        except Exception as exc:
            return RunResponse(status="error", error=str(exc))


# Не забудьте обновить get_service():
# _service_instance = TextGeneratorService()
```

---

## API документация

### GET /health

Простая проверка работоспособности.

**Ответ:**

```json
{"status": "ok"}
```

---

### GET /info

Возвращает метаданные сервиса: тип входных данных, схему параметров и схему результата.

**Ответ:**

```json
{
  "input_type": "text_and_image",
  "input_schema": {
    "type": "object",
    "properties": {
      "echo_prefix": {
        "type": "string",
        "description": "Префикс перед эхо-текстом.",
        "default": "You said: "
      }
    }
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "echo": {"type": "string"},
      "text_length": {"type": "integer"},
      "image_info": {"type": "object"}
    }
  }
}
```

**Поля:**

| Поле | Тип | Описание |
|---|---|---|
| `input_type` | `"text"` \| `"image"` \| `"text_and_image"` | Тип контента, который сервис ожидает |
| `input_schema` | object | JSON Schema для параметров `extra_body` |
| `output_schema` | object | JSON Schema для поля `result` в ответе `/run` |

---

### POST /run

Выполняет основную логику сервиса. Формат запроса **одинаков для всех сервисов**.

**Запрос (текст):**

```json
{
  "content": "Привет, мир!",
  "extra_body": {}
}
```

**Запрос (мультимодальный):**

```json
{
  "content": [
    {"type": "text", "text": "Что на картинке?"},
    {"type": "image", "image": "<base64>"}
  ],
  "extra_body": {"temperature": 0.7}
}
```

**Поля запроса:**

| Поле | Тип | Обязательное | Описание |
|---|---|---|---|
| `content` | `string` или `array` | Да | Основной ввод: строка (текст) или список ContentPart |
| `extra_body` | `object` | Нет | Дополнительные параметры (default: `{}`) |

**ContentPart (элементы списка content):**

| Тип | Поля | Описание |
|---|---|---|
| `{"type": "text", "text": "..."}` | `text` — строка | Текстовая часть |
| `{"type": "image", "image": "..."}` | `image` — base64 | Картинка (PNG, JPEG и т.д.) |

**Успешный ответ:**

```json
{
  "status": "success",
  "result": {
    "echo": "You said: Привет, мир!",
    "text_length": 11
  },
  "error": null
}
```

**Ответ с ошибкой:**

```json
{
  "status": "error",
  "result": null,
  "error": "Описание ошибки"
}
```

---

## Нагрузочное тестирование

### Запуск Locust (веб-интерфейс)

```bash
# Сначала запустите сервис
docker compose up --build -d

# Запустите Locust (веб-интерфейс на http://localhost:8089)
locust -f locustfile.py --host http://localhost:8000
```

### Запуск Locust (headless, без браузера)

```bash
locust -f locustfile.py --host http://localhost:8000 \
  --headless -u 10 -r 2 -t 60s
```

Где:
- `-u 10` — 10 виртуальных пользователей
- `-r 2` — 2 новых пользователя в секунду
- `-t 60s` — длительность теста 60 секунд

### Как работает Locust

1. При старте вызывает `GET /info` для определения `input_type`.
2. Генерирует подходящий контент:
   - `"text"` → `{"content": "случайный текст", "extra_body": {}}`
   - `"image"` → `{"content": [{"type": "image", "image": "<base64>"}], "extra_body": {}}`
   - `"text_and_image"` → `{"content": [{"type": "text", "text": "..."}, {"type": "image", "image": "<base64>"}], "extra_body": {}}`
3. Отправляет запросы: `/run` (вес 10) и `/info` (вес 1).

---

## Требования к контейнеру

1. **Порт:** Контейнер должен слушать порт **8000**.
2. **Эндпоинты:**
   - `GET /health` — возвращает `{"status": "ok"}`.
   - `GET /info` — возвращает метаданные сервиса.
   - `POST /run` — принимает данные и возвращает результат.
3. **Формат данных:** JSON, как описано выше.
4. **Время ответа:** Желательно не более 60 секунд на один запрос.
5. **Обработка ошибок:** Сервис должен корректно обрабатывать некорректные входные данные и возвращать `status: "error"` с описанием ошибки.
6. **Структура запроса:** Единый формат для всех сервисов — `content` (строка или список) + `extra_body` (словарь).
