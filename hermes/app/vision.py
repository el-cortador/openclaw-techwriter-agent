from __future__ import annotations

import base64
import mimetypes

from openai import OpenAI

from app import config
from app.models import IncomingAttachment
from app.service_client import ServiceError


def describe_ui_screenshot(attachment: IncomingAttachment, user_text: str) -> str:
    if not config.OPENROUTER_API_KEY:
        raise ServiceError("OPENROUTER_API_KEY не задан для обработки изображений.")

    media_type = attachment.content_type or mimetypes.guess_type(attachment.filename)[0] or "image/png"
    encoded = base64.b64encode(attachment.path.read_bytes()).decode("ascii")

    prompt = (
        "Ты технический писатель. По скриншоту интерфейса составь user guide на русском языке.\n"
        "Описывай только видимые элементы и очевидное поведение. Не придумывай скрытые функции.\n"
        "Если часть текста не читается или экран неполный, явно укажи ограничение.\n"
        "Структура ответа:\n"
        "1. Назначение экрана\n"
        "2. Основные элементы\n"
        "3. Порядок действий пользователя\n"
        "4. Проверки и ограничения\n"
        "5. Результат действия\n"
    )
    if user_text.strip():
        prompt += f"\nДополнительный запрос пользователя:\n{user_text.strip()}"

    client = OpenAI(
        api_key=config.OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )
    response = client.chat.completions.create(
        model=config.HERMES_VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{encoded}",
                        },
                    },
                ],
            }
        ],
        temperature=0.2,
        max_tokens=4096,
    )
    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise ServiceError("Vision-модель вернула пустой результат.")
    return content
