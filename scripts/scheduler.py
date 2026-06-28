"""등록된 일정(data/state.json)에 따라 매주 지정 요일/시각에 템플릿을 발송하는
상시 실행 프로세스입니다. pm2로 실행하세요.

    pm2 start ecosystem.config.js --only raffle-scheduler

template에 placeholder(기본 "@태그")가 포함되어 있으면 발송 시점에 대상 채팅
참여자 중 봇을 제외하고 무작위로 당첨자를 뽑아 그 자리에 태그합니다.
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telethon import helpers

from raffle.client import build_client
from raffle.mention import mention_replacement
from raffle.send import render_with_replacements
from raffle.state import load_state
from raffle.template import SAVED_MESSAGES, fetch_template
from raffle.winner import get_eligible_participants, pick_random_winner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("scheduler")

RELOAD_INTERVAL_SECONDS = 30
TIMEZONE = "Asia/Seoul"


def build_followup(winner, count) -> tuple[str, list]:
    """비프리미엄(포워딩) 모드에서, 포워딩된 메시지에 답장으로 붙일 당첨자/인원수 줄을 만듭니다.
    멘션(@username, user_id 태그)은 프리미엄 없이도 동작하므로 여기서만 합성합니다.
    """
    text = ""
    entities = []
    if winner is not None:
        repl = mention_replacement(winner)
        text += "🎉 당첨자: "
        offset = len(helpers.add_surrogate(text))
        wtext = repl["text"]
        text += wtext
        length = len(helpers.add_surrogate(wtext))
        if repl.get("entity"):
            entities.append(repl["entity"](offset, length))
        text += " 🎉"
    if count is not None:
        if text:
            text += "\n"
        text += f"👥 참가자: {count}명"
    return text, entities


async def fire_stage(
    client,
    stage_id: str,
    info: dict,
    target_chat,
    placeholder: str,
    count_placeholder: str,
    is_premium: bool,
):
    if not target_chat:
        log.warning("target_chat이 설정되지 않아 %s단계를 건너뜁니다 (/chat 으로 설정하세요)", stage_id)
        return

    try:
        template = await fetch_template(client, info["template_id"])
    except ValueError as e:
        log.error("%s단계 템플릿 조회 실패: %s", stage_id, e)
        return

    message_text = template.message or ""
    needs_winner = bool(placeholder and placeholder in message_text)
    needs_count = bool(count_placeholder and count_placeholder in message_text)

    winner = None
    if needs_winner:
        try:
            winner = await pick_random_winner(client, target_chat)
        except ValueError as e:
            log.error("%s단계 당첨자 추첨 실패: %s", stage_id, e)
            return
        log.info("%s단계: 당첨자 추첨됨 (user_id=%s)", stage_id, winner.id)

    count = None
    if needs_count:
        try:
            count = len(await get_eligible_participants(client, target_chat))
        except Exception as e:
            log.error("%s단계 참여자 수 조회 실패: %s", stage_id, e)
            return
        log.info("%s단계: 참여자 수 %d명", stage_id, count)

    if is_premium:
        # 프리미엄 계정: 원본 text+entities를 그대로 재합성해서 보냄(커스텀 이모지 보존 + 인라인 치환).
        replacements = {}
        if needs_winner:
            replacements[placeholder] = mention_replacement(winner)
        if needs_count:
            replacements[count_placeholder] = {"text": str(count)}
        text, entities = render_with_replacements(template, replacements)
        await client.send_message(
            target_chat, text, formatting_entities=entities, parse_mode=None, link_preview=False
        )
        log.info("%s단계 발송 완료(compose) -> %s", stage_id, target_chat)
        return

    # 비프리미엄 계정: 새로 합성하면 커스텀 이모지가 깨지므로, 원본을 그대로 '포워딩'해서 보존.
    # (drop_author=True 로 '전달됨' 표시 없이 새 메시지처럼 보냄)
    fwd = await client.forward_messages(
        target_chat, info["template_id"], from_peer=SAVED_MESSAGES, drop_author=True
    )
    sent = fwd[0] if isinstance(fwd, list) else fwd

    if needs_winner or needs_count:
        ftext, fentities = build_followup(winner, count)
        if ftext:
            await client.send_message(
                target_chat,
                ftext,
                formatting_entities=fentities,
                parse_mode=None,
                link_preview=False,
                reply_to=sent.id,
            )
    log.info("%s단계 발송 완료(forward) -> %s", stage_id, target_chat)


def sync_jobs(scheduler: AsyncIOScheduler, client, state: dict, is_premium: bool):
    scheduler.remove_all_jobs()
    target_chat = state.get("target_chat")
    placeholder = state.get("placeholder", "@태그")
    count_placeholder = state.get("count_placeholder", "{인원수}")
    for stage_id, info in state.get("stages", {}).items():
        try:
            hh, mm = (int(x) for x in info["time"].split(":"))
            trigger = CronTrigger(
                day_of_week=info["weekday"], hour=hh, minute=mm, timezone=TIMEZONE
            )
        except (KeyError, ValueError) as e:
            log.error(
                "%s단계 스케줄 등록 실패 (등록값 확인 후 /%s 으로 다시 등록하세요): %s",
                stage_id,
                stage_id,
                e,
            )
            continue
        scheduler.add_job(
            fire_stage,
            trigger=trigger,
            args=[
                client,
                stage_id,
                info,
                target_chat,
                placeholder,
                count_placeholder,
                is_premium,
            ],
            id=f"stage-{stage_id}",
            misfire_grace_time=120,
            replace_existing=True,
        )
        log.info("%s단계 스케줄 등록: 요일#%s %02d:%02d", stage_id, info["weekday"], hh, mm)


async def watch_state(scheduler: AsyncIOScheduler, client, is_premium: bool):
    last_snapshot = None
    while True:
        state = load_state()
        snapshot = json.dumps(state, sort_keys=True)
        if snapshot != last_snapshot:
            sync_jobs(scheduler, client, state, is_premium)
            last_snapshot = snapshot
        await asyncio.sleep(RELOAD_INTERVAL_SECONDS)


async def main():
    client = build_client()
    await client.start()

    me = await client.get_me()
    is_premium = bool(getattr(me, "premium", False))
    if is_premium:
        log.info("프리미엄 계정 감지됨: 커스텀 이모지를 그대로 합성해서 발송합니다(인라인 치환).")
    else:
        log.warning(
            "비프리미엄 계정입니다. 커스텀(프리미엄) 이모지는 '새로 작성한 메시지'로는 보낼 수 없어, "
            "원본 템플릿을 그대로 '포워딩'해서 발송합니다(이모지 보존). 당첨자/인원수는 그 메시지에 "
            "답장으로 덧붙습니다. 인라인 태그+이모지를 원하면 발송 계정에 텔레그램 프리미엄이 필요합니다."
        )

    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.start()

    log.info("스케줄러 시작됨. data/state.json 을 %d초마다 확인합니다.", RELOAD_INTERVAL_SECONDS)
    await watch_state(scheduler, client, is_premium)


if __name__ == "__main__":
    asyncio.run(main())
