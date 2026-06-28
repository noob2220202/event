import random

from telethon import TelegramClient
from telethon.tl.types import User


async def pick_random_winner(client: TelegramClient, chat) -> User:
    """대상 채팅의 참여자 중 봇을 제외하고 한 명을 무작위로 뽑습니다."""
    participants = await client.get_participants(chat)
    eligible = [p for p in participants if not p.bot]
    if not eligible:
        raise ValueError("추첨 가능한 참가자가 없습니다 (참여자가 없거나 전부 봇).")
    return random.choice(eligible)
