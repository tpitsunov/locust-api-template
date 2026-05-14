"""
Базовый класс сервиса и демо-реализация.

Этот файл — ЕДИНСТВЕННОЕ место, которое нужно менять студенту.
Всё остальное (FastAPI, схемы, Docker) работает автоматически.

КАК ПОЛЬЗОВАТЬСЯ:
1. Прочитайте комментарии к ServiceBase — там описаны все методы.
2. Посмотрите на DemoService как на рабочий пример.
3. Создайте свой класс-наследник ServiceBase.
4. Обновите функцию get_service() в конце файла.
"""

from __future__ import annotations

import base64
import io
from abc import ABC, abstractmethod
from typing import Any

from app.schemas import (
    ContentPartImage,
    ContentPartText,
    InfoResponse,
    InputType,
    RunRequest,
    RunResponse,
    Schema,
)


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  БАЗОВЫЙ КЛАСС — НЕ ИЗМЕНЯЙТЕ ЕГО                                         ║
# ║  Все helper-методы (get_text, get_image) уже реализованы ниже.            ║
# ╚════════════════════════════════════════════════════════════════════════════╝


class ServiceBase(ABC):
    """Абстрактный базовый класс для всех сервисов.

    Каждый студент должен унаследовать этот класс и реализовать два метода:
      - get_info() — возвращает тип входных данных сервиса.
      - run()      — основная логика обработки запроса.

    Также доступны вспомогательные методы (helpers):
      - get_text(request)  — извлекает текст из content.
      - get_image(request) — извлекает base64 картинку из content.
    """

    @abstractmethod
    def get_info(self) -> InfoResponse:
        """Вернуть метаданные сервиса.

        input_type определяет, какой контент будет отправлять нагрузочный тест:
          - InputType.TEXT           → content — строка с текстом
          - InputType.IMAGE          → content — список с одной картинкой
          - InputType.TEXT_AND_IMAGE → content — список с текстом и картинкой

        input_schema — JSON Schema для параметров extra_body.
        output_schema — JSON Schema для поля result в ответе.
        """
        ...

    @abstractmethod
    def run(self, request: RunRequest) -> RunResponse:
        """Выполнить основную логику сервиса.

        Аргумент request содержит:
          - request.content    : str | list[ContentPart]
              Строка = обычный текст.
              Список = типизированные части (текст + картинка).
          - request.extra_body : dict
              Дополнительные параметры (temperature, max_tokens, ...).

        Верните RunResponse(status="success", result={...}) или
        RunResponse(status="error", error="описание ошибки").
        """
        ...

    # ------------------------------------------------------------------
    # Helper methods — вспомогательные методы для извлечения данных
    # ------------------------------------------------------------------

    def get_text(self, request: RunRequest) -> str | None:
        """Извлечь текст из content.

        Если content — строка, возвращает её как есть.
        Если content — список, ищет первую часть с type="text".
        Если текст не найден, возвращает None.

        Пример использования:
            text = self.get_text(request)
            if text is None:
                return RunResponse(status="error", error="Текст не передан")

        Args:
            request: объект RunRequest с полем content.

        Returns:
            Строка с текстом или None.
        """
        if isinstance(request.content, str):
            return request.content

        for part in request.content:
            if isinstance(part, ContentPartText):
                return part.text

        return None

    def get_image(self, request: RunRequest) -> str | None:
        """Извлечь base64-кодированную картинку из content.

        Ищет первую часть с type="image" в списке content.
        Если content — строка (текст), возвращает None.

        Пример использования:
            image_b64 = self.get_image(request)
            if image_b64 is None:
                return RunResponse(status="error", error="Картинка не передана")
            image_bytes = base64.b64decode(image_b64)

        Args:
            request: объект RunRequest с полем content.

        Returns:
            Строка с base64-кодированной картинкой или None.
        """
        if isinstance(request.content, str):
            return None

        for part in request.content:
            if isinstance(part, ContentPartImage):
                return part.image

        return None


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  СТУДЕНТУ: Ниже находится демо-сервис. Замените его на свою реализацию.   ║
# ║  1. Напишите свой класс-наследник ServiceBase.                            ║
# ║  2. Обновите функцию get_service() в конце файла.                         ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


class DemoService(ServiceBase):
    """Демо-сервис — эхо текста + информация о картинке.

    Этот сервис показывает, как:
      - Использовать get_text() для получения текста.
      - Использовать get_image() для получения картинки.
      - Работать с extra_body для дополнительных параметров.
      - Формировать RunResponse.

    Замените этот класс на свою реализацию!
    """

    def get_info(self) -> InfoResponse:
        return InfoResponse(
            input_type=InputType.TEXT_AND_IMAGE,
            input_schema=Schema.of(
                echo_prefix=Schema.string(
                    "Префикс перед эхо-текстом", default="You said: "
                ),
            ),
            output_schema=Schema.of(
                echo=Schema.string("Текст с префиксом"),
                text_length=Schema.integer("Длина исходного текста"),
                image_info=Schema.object(
                    "Информация о картинке",
                    size_bytes=Schema.integer("Размер в байтах"),
                    width=Schema.integer("Ширина"),
                    height=Schema.integer("Высота"),
                    format=Schema.string("Формат (PNG, JPEG, ...)"),
                    mode=Schema.string("Режим (RGB, RGBA, ...)"),
                ),
            ),
        )

    def run(self, request: RunRequest) -> RunResponse:
        """Основная логика демо-сервиса.

        Шаги:
          1. Извлечь текст через get_text().
          2. Извлечь картинку через get_image().
          3. Прочитать extra_body для дополнительных параметров.
          4. Выполнить обработку и вернуть результат.
        """
        try:
            result: dict[str, Any] = {}

            # Извлекаем текст с помощью helper-метода
            text = self.get_text(request)
            if text is not None:
                # Читаем дополнительный параметр из extra_body
                prefix = request.extra_body.get("echo_prefix", "You said: ")
                result["echo"] = f"{prefix}{text}"
                result["text_length"] = len(text)

            # Извлекаем картинку с помощью helper-метода
            image_b64 = self.get_image(request)
            if image_b64 is not None:
                image_bytes = base64.b64decode(image_b64)
                result["image_info"] = self._describe_image(image_bytes)

            return RunResponse(status="success", result=result)
        except Exception as exc:
            return RunResponse(status="error", error=str(exc))

    @staticmethod
    def _describe_image(image_bytes: bytes) -> dict[str, Any]:
        """Определить размеры и формат картинки через Pillow."""
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        return {
            "size_bytes": len(image_bytes),
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "mode": img.mode,
        }


# ╔════════════════════════════════════════════════════╗
# ║  СТУДЕНТУ: Обновите функцию get_service() ниже.    ║
# ║  Замените DemoService на имя вашего класса.        ║
# ╚════════════════════════════════════════════════════╝


_service_instance: ServiceBase | None = None


def get_service() -> ServiceBase:
    """
    Фабрика — возвращает singleton-экземпляр сервиса.
    Замените DemoService() на свой класс.
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = DemoService()
    return _service_instance
