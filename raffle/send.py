from telethon import TelegramClient
from telethon.tl.types import Message

from .entities import Replacement, remap_entities


def render_with_replacements(template: Message, replacements: dict[str, Replacement]):
    """템플릿 메시지의 원본 text+entities에 placeholder 치환을 적용한 결과를 반환합니다."""
    raw_text = template.message or ""
    raw_entities = template.entities or []
    return remap_entities(raw_text, raw_entities, replacements)


async def send_with_replacements(
    client: TelegramClient,
    template: Message,
    target_chat,
    replacements: dict[str, Replacement],
):
    text, entities = render_with_replacements(template, replacements)
    return await client.send_message(
        target_chat,
        text,
        formatting_entities=entities,
        parse_mode=None,
        link_preview=False,
    )
