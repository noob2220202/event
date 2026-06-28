from telethon import TelegramClient

from .config import load_settings


def build_client() -> TelegramClient:
    """유저 세션(.session)을 사용하는 Telethon 클라이언트를 생성합니다.

    Bot API 토큰이 아니라 실제 계정으로 로그인하는 세션이므로,
    프리미엄 커스텀 이모지를 포함한 메시지를 그대로 읽고 보낼 수 있습니다.
    """
    settings = load_settings()
    return TelegramClient(settings.session_name, settings.api_id, settings.api_hash)
