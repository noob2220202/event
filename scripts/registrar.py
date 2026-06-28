"""저장된 메시지(Saved Messages)에서 보내는 명령을 듣고 템플릿/발송 일정을 등록하는
상시 실행 프로세스입니다. pm2로 실행하세요.

    pm2 start ecosystem.config.js --only raffle-registrar

명령 형식은 /help 를 참고하세요.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telethon import events

from raffle.client import build_client
from raffle.commands import (
    DeleteStage,
    Help,
    ListState,
    RegisterStage,
    SetChat,
    SetCountPlaceholder,
    SetPlaceholder,
    parse_command,
)
from raffle.state import load_state, save_state
from raffle.template import SAVED_MESSAGES
from raffle.weekday import WEEKDAY_NAMES_KO

HELP_TEXT = (
    "사용법 (저장된 메시지에서 입력):\n"
    "  템플릿 메시지에 답장 -> /<단계번호> <요일> <HH:MM>   예) /1 일 18:00\n"
    "  /del <단계번호>            단계 등록 삭제\n"
    "  /chat <대상채팅>           발송 대상 채팅 설정, 예) /chat @mychannel\n"
    "  /placeholder <문자열>      당첨자 태그 placeholder 변경 (기본값: @태그)\n"
    "  /countplaceholder <문자열> 참여자 수 placeholder 변경 (기본값: {인원수})\n"
    "  /list                     현재 등록 상태 보기\n"
    "\n"
    "대상 채팅을 바로 그 채팅 안에서 설정하려면, 해당 그룹/채널에 직접\n"
    "/groupset 이라고 보내세요 (저장된 메시지 아님). 그 채팅이 바로 발송\n"
    "대상으로 등록되고, 명령/확인 메시지는 몇 초 후 자동 삭제됩니다.\n"
)


def render_state_summary(state: dict) -> str:
    lines = [
        f"대상 채팅: {state.get('target_chat') or '(미설정, /chat 으로 설정하세요)'}",
        f"태그 placeholder: {state.get('placeholder')}",
        f"참여자 수 placeholder: {state.get('count_placeholder', '{인원수}')}",
        "단계:",
    ]
    stages = state.get("stages", {})
    if not stages:
        lines.append("  (없음)")
    for stage, info in sorted(stages.items(), key=lambda kv: int(kv[0])):
        lines.append(
            f"  {stage} -> template_id={info['template_id']} "
            f"매주 {WEEKDAY_NAMES_KO[info['weekday']]}요일 {info['time']}"
        )
    return "\n".join(lines)


async def handle(event):
    try:
        command = parse_command(event.raw_text or "")
    except ValueError as e:
        await event.reply(f"⚠️ {e}")
        return

    if command is None:
        return

    state = load_state()

    if isinstance(command, RegisterStage):
        if not event.is_reply:
            await event.reply("⚠️ 등록할 템플릿 메시지에 답장(reply)으로 명령을 보내주세요.")
            return
        replied = await event.get_reply_message()
        state["stages"][command.stage] = {
            "template_id": replied.id,
            "weekday": command.weekday,
            "time": command.time,
        }
        save_state(state)
        await event.reply(
            f"✅ {command.stage}단계 등록 완료: 매주 {WEEKDAY_NAMES_KO[command.weekday]}요일 {command.time}"
        )

    elif isinstance(command, DeleteStage):
        if state["stages"].pop(command.stage, None) is not None:
            save_state(state)
            await event.reply(f"🗑️ {command.stage}단계 등록 삭제됨")
        else:
            await event.reply(f"등록된 {command.stage}단계가 없습니다.")

    elif isinstance(command, SetChat):
        state["target_chat"] = command.chat
        save_state(state)
        await event.reply(f"✅ 발송 대상 채팅 설정: {command.chat}")

    elif isinstance(command, SetPlaceholder):
        state["placeholder"] = command.placeholder
        save_state(state)
        await event.reply(f"✅ 태그 placeholder 변경: {command.placeholder}")

    elif isinstance(command, SetCountPlaceholder):
        state["count_placeholder"] = command.placeholder
        save_state(state)
        await event.reply(f"✅ 참여자 수 placeholder 변경: {command.placeholder}")

    elif isinstance(command, ListState):
        await event.reply(render_state_summary(state))

    elif isinstance(command, Help):
        await event.reply(HELP_TEXT)


async def handle_groupset(event):
    """채널/그룹 안에서 /groupset 을 받으면 그 채팅 자체를 발송 대상으로 등록합니다."""
    state = load_state()
    state["target_chat"] = event.chat_id
    save_state(state)

    chat = await event.get_chat()
    name = getattr(chat, "title", None) or getattr(chat, "username", None) or str(event.chat_id)
    reply = await event.reply(f"✅ 발송 대상 채팅 설정: {name} ({event.chat_id})")

    await asyncio.sleep(3)
    await event.client.delete_messages(event.chat_id, [event.id, reply.id])


async def main():
    client = build_client()
    await client.start()

    me = await client.get_me()

    @client.on(events.NewMessage(chats=SAVED_MESSAGES, outgoing=True))
    async def _(event):
        await handle(event)

    @client.on(events.NewMessage(outgoing=True, pattern=r"^/groupset\s*$"))
    async def _(event):
        if event.chat_id == me.id:
            return  # 저장된 메시지(자기 자신)는 그룹 설정 대상이 아님
        await handle_groupset(event)

    print(f"등록 리스너 시작됨 ({me.first_name}). 저장된 메시지에서 명령을 기다립니다. (/help)")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
