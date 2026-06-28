import random

from telethon import TelegramClient
from telethon.tl.types import User


async def get_eligible_participants(client: TelegramClient, chat) -> list[User]:
    """대상 채팅의 참여자 중 봇을 제외한 목록을 가져옵니다."""
    participants = await client.get_participants(chat)
    return [p for p in participants if not p.bot]


async def pick_random_winner(client: TelegramClient, chat) -> User:
    """대상 채팅의 참여자 중 봇을 제외하고 한 명을 무작위로 뽑습니다."""
    eligible = await get_eligible_participants(client, chat)
    if not eligible:
        raise ValueError("추첨 가능한 참가자가 없습니다 (참여자가 없거나 전부 봇).")
    return random.choice(eligible)
