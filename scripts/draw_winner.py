"""저장된 메시지 템플릿의 태그 placeholder를 실제 유저 멘션으로 치환해 전송합니다.

예)
    python -m scripts.draw_winner \\
        --template-id 123 \\
        --chat @my_event_channel \\
        --user @winner_username \\
        --dry-run
"""
import argparse
import asyncio

from raffle.client import build_client
from raffle.mention import mention_replacement
from raffle.send import render_with_replacements
from raffle.template import fetch_template


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template-id", type=int, required=True, help="저장된 메시지의 message id")
    parser.add_argument("--chat", required=True, help="전송할 대상 채팅 (예: @channel, -1001234567890)")
    parser.add_argument("--user", required=True, help="태그할 유저 (예: @username, 숫자 user_id)")
    parser.add_argument(
        "--placeholder",
        default="@태그",
        help="템플릿 안에서 실제 멘션으로 바꿔칠 placeholder 문자열 (기본값: @태그)",
    )
    parser.add_argument(
        "--extra",
        action="append",
        default=[],
        help="추가 치환 KEY=VALUE 형식, 여러 번 지정 가능 (예: --extra '{{COUNT}}=5668명')",
    )
    parser.add_argument("--dry-run", action="store_true", help="전송하지 않고 치환 결과만 출력")
    args = parser.parse_args()

    client = build_client()
    await client.start()

    template = await fetch_template(client, args.template_id)
    target_user = await client.get_entity(args.user)

    replacements = {args.placeholder: mention_replacement(target_user)}
    for item in args.extra:
        key, _, value = item.partition("=")
        replacements[key] = {"text": value, "entity": None}

    text, entities = render_with_replacements(template, replacements)

    if args.dry_run:
        print("--- 치환 결과 (dry-run, 전송하지 않음) ---")
        print(text)
        print(f"--- entities ({len(entities)}) ---")
        for e in entities:
            print(e)
    else:
        await client.send_message(
            args.chat,
            text,
            formatting_entities=entities,
            parse_mode=None,
            link_preview=False,
        )
        print(f"전송 완료 -> {args.chat}")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
