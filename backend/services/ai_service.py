from __future__ import annotations

from anthropic import APIConnectionError, APIStatusError, AsyncAnthropic
from fastapi import HTTPException, status

from backend.core.config import get_settings

_MODEL = "claude-sonnet-4-6"

_INTERPRET_SYSTEM = """\
Ты — аналитик маркетплейса Wildberries. Тебе предоставлены данные о марже товаров продавца.
Составь структурированный отчёт строго на русском языке, разбитый на три раздела:

## Диагноз
Кратко опиши текущее состояние ассортимента: какие товары прибыльны, какие убыточны, \
общую картину маржинальности.

## Рекомендации
Конкретные действия для улучшения маржинальности (цены, комиссии, логистика, ассортимент). \
Используй цифры из данных.

## Риски
Основные риски для прибыльности с учётом текущей структуры ассортимента.

Отвечай только на русском языке. Будь конкретным, используй числа из данных."""

_CHAT_SYSTEM_PREFIX = """\
Ты — аналитик маркетплейса Wildberries, консультируешь продавца по его данным.
Отвечай кратко и конкретно, только на русском языке. Опирайся на контекст анализа.

Контекст анализа продавца:
"""


def _get_client() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=get_settings().ANTHROPIC_API_KEY)


def _service_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Сервис AI временно недоступен. Пожалуйста, попробуйте позже.",
    )


async def generate_interpretation(products_text: str) -> str:
    """Вызывает Claude и возвращает интерпретацию с тремя разделами."""
    try:
        msg = await _get_client().messages.create(
            model=_MODEL,
            max_tokens=2000,
            system=_INTERPRET_SYSTEM,
            messages=[{"role": "user", "content": products_text}],
        )
        return msg.content[0].text
    except (APIStatusError, APIConnectionError) as exc:
        raise _service_unavailable() from exc


async def chat_reply(
    analysis_context: str,
    history: list[dict[str, str]],
    user_message: str,
) -> str:
    """Возвращает ответ ассистента, используя последние 5 сообщений из истории."""
    system = _CHAT_SYSTEM_PREFIX + analysis_context
    messages = list(history[-5:]) + [{"role": "user", "content": user_message}]
    try:
        msg = await _get_client().messages.create(
            model=_MODEL,
            max_tokens=1000,
            system=system,
            messages=messages,
        )
        return msg.content[0].text
    except (APIStatusError, APIConnectionError) as exc:
        raise _service_unavailable() from exc
