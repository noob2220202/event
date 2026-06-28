"""등록된 일정(data/state.json)에 따라 매주 지정 요일/시각에 템플릿을 발송하는
상시 실행 프로세스입니다. pm2로 실행하세요.

    pm2 start ecosystem.config.js --only raffle-scheduler

template에 placeholder(기본 "@태그")가 포함되어 있으면 발송 시점에 대상 채팅
참여자 중 봇을 제외하고 무작위로 당첨자를 뽑아 그 자리에 태그합니다.
"""
import asyncio
import json
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from raffle.client import build_client
from raffle.mention import mention_replacement
from raffle.send import render_with_replacements
from raffle.state import load_state
from raffle.template import fetch_template
from raffle.winner import pick_random_winner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("scheduler")

RELOAD_INTERVAL_SECONDS = 30
TIMEZONE = "Asia/Seoul"


async def fire_stage(client, stage_id: str, info: dict, target_chat, placeholder: str):
    if not target_chat:
        log.warning("target_chat이 설정되지 않아 %s단계를 건너뜁니다 (/chat 으로 설정하세요)", stage_id)
        return

    try:
        template = await fetch_template(client, info["template_id"])
    except ValueError as e:
        log.error("%s단계 템플릿 조회 실패: %s", stage_id, e)
        return

    replacements = {}
    if placeholder and placeholder in (template.message or ""):
        try:
            winner = await pick_random_winner(client, target_chat)
        except ValueError as e:
            log.error("%s단계 당첨자 추첨 실패: %s", stage_id, e)
            return
        replacements[placeholder] = mention_replacement(winner)
        log.info("%s단계: 당첨자 추첨됨 (user_id=%s)", stage_id, winner.id)

    text, entities = render_with_replacements(template, replacements)
    await client.send_message(
        target_chat, text, formatting_entities=entities, parse_mode=None, link_preview=False
    )
    log.info("%s단계 발송 완료 -> %s", stage_id, target_chat)


def sync_jobs(scheduler: AsyncIOScheduler, client, state: dict):
    scheduler.remove_all_jobs()
    target_chat = state.get("target_chat")
    placeholder = state.get("placeholder", "@태그")
    for stage_id, info in state.get("stages", {}).items():
        hh, mm = (int(x) for x in info["time"].split(":"))
        trigger = CronTrigger(day_of_week=info["weekday"], hour=hh, minute=mm, timezone=TIMEZONE)
        scheduler.add_job(
            fire_stage,
            trigger=trigger,
            args=[client, stage_id, info, target_chat, placeholder],
            id=f"stage-{stage_id}",
            misfire_grace_time=120,
            replace_existing=True,
        )
        log.info("%s단계 스케줄 등록: 요일#%s %02d:%02d", stage_id, info["weekday"], hh, mm)


async def watch_state(scheduler: AsyncIOScheduler, client):
    last_snapshot = None
    while True:
        state = load_state()
        snapshot = json.dumps(state, sort_keys=True)
        if snapshot != last_snapshot:
            sync_jobs(scheduler, client, state)
            last_snapshot = snapshot
        await asyncio.sleep(RELOAD_INTERVAL_SECONDS)


async def main():
    client = build_client()
    await client.start()

    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.start()

    log.info("스케줄러 시작됨. data/state.json 을 %d초마다 확인합니다.", RELOAD_INTERVAL_SECONDS)
    await watch_state(scheduler, client)


if __name__ == "__main__":
    asyncio.run(main())
