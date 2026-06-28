from telethon.tl.types import MessageEntityMention, MessageEntityMentionName, User

from .entities import Replacement


def mention_replacement(user: User) -> Replacement:
    """대상 유저를 멘션(태그)하기 위한 치환 텍스트 + entity factory를 만듭니다.

    username이 있으면 일반 @username 멘션, 없으면 user_id 기반의
    text-mention(MessageEntityMentionName)으로 표시 이름을 태그합니다.
    """
    if user.username:
        text = f"@{user.username}"

        def factory(offset: int, length: int):
            return MessageEntityMention(offset=offset, length=length)

        return {"text": text, "entity": factory}

    display_name = " ".join(filter(None, [user.first_name, user.last_name])) or "user"

    def factory(offset: int, length: int):
        return MessageEntityMentionName(offset=offset, length=length, user_id=user.id)

    return {"text": display_name, "entity": factory}
