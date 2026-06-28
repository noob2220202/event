import re
from dataclasses import dataclass
from typing import Optional, Union

from .weekday import parse_weekday

_STAGE_RE = re.compile(r"^/(\d+)\s+(\S+)\s+(\d{1,2}):(\d{2})\s*$")
_DEL_RE = re.compile(r"^/del\s+(\d+)\s*$")
_CHAT_RE = re.compile(r"^/chat\s+(\S+)\s*$")
_PLACEHOLDER_RE = re.compile(r"^/placeholder\s+(.+)$")
_LIST_RE = re.compile(r"^/list\s*$")
_HELP_RE = re.compile(r"^/help\s*$")


@dataclass
class RegisterStage:
    stage: str
    weekday: int
    time: str  # "HH:MM"


@dataclass
class DeleteStage:
    stage: str


@dataclass
class SetChat:
    chat: str


@dataclass
class SetPlaceholder:
    placeholder: str


@dataclass
class ListState:
    pass


@dataclass
class Help:
    pass


Command = Union[RegisterStage, DeleteStage, SetChat, SetPlaceholder, ListState, Help]


def parse_command(text: str) -> Optional[Command]:
    """저장된 메시지에 입력한 명령 한 줄을 구조화된 Command로 변환합니다.
    명령이 아니면 None, 형식은 맞지만 값이 잘못되면 ValueError를 던집니다.
    """
    text = (text or "").strip()

    m = _STAGE_RE.match(text)
    if m:
        stage, weekday_token, hh, mm = m.groups()
        weekday = parse_weekday(weekday_token)
        return RegisterStage(stage=stage, weekday=weekday, time=f"{int(hh):02d}:{int(mm):02d}")

    m = _DEL_RE.match(text)
    if m:
        return DeleteStage(stage=m.group(1))

    m = _CHAT_RE.match(text)
    if m:
        return SetChat(chat=m.group(1))

    m = _PLACEHOLDER_RE.match(text)
    if m:
        return SetPlaceholder(placeholder=m.group(1).strip())

    if _LIST_RE.match(text):
        return ListState()

    if _HELP_RE.match(text):
        return Help()

    return None
