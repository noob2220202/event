"""저장된 메시지(Saved Messages)에서 보내는 명령을 듣고 템플릿/발송 일정을 등록하는
상시 실행 프로세스입니다. pm2로 실행하세요.

    pm2 start ecosystem.config.js --only raffle-registrar

명령 형식은 /help 를 참고하세요.
"""
import asyncio

from telethon import events

from raffle.client import build_client
from raffle.commands import (
    DeleteStage,
    Help,
    ListState,
    RegisterStage,
    SetChat,
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
    "  /placeholder <문자열>      태그 placeholder 변경 (기본값: @태그)\n"
    "  /list                     현재 등록 상태 보기\n"
)


def render_state_summary(state: dict) -> str:
    lines = [
        f"대상 채팅: {state.get('target_chat') or '(미설정, /chat 으로 설정하세요)'}",
        f"placeholder: {state.get('placeholder')}",
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
        await event.reply(f"✅ placeholder 변경: {command.placeholder}")

    elif isinstance(command, ListState):
        await event.reply(render_state_summary(state))

    elif isinstance(command, Help):
        await event.reply(HELP_TEXT)


async def main():
    client = build_client()
    await client.start()

    @client.on(events.NewMessage(chats=SAVED_MESSAGES, outgoing=True))
    async def _(event):
        await handle(event)

    me = await client.get_me()
    print(f"등록 리스너 시작됨 ({me.first_name}). 저장된 메시지에서 명령을 기다립니다. (/help)")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
