from telethon import TelegramClient
from telethon.tl.types import Message

SAVED_MESSAGES = "me"


async def fetch_template(client: TelegramClient, message_id: int) -> Message:
    """본인의 저장된 메시지(Saved Messages)에서 message_id로 템플릿을 가져옵니다."""
    msg = await client.get_messages(SAVED_MESSAGES, ids=message_id)
    if msg is None:
        raise ValueError(f"저장된 메시지에서 id={message_id} 를 찾을 수 없습니다.")
    return msg
