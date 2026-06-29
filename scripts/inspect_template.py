"""템플릿 메시지에 커스텀(프리미엄) 이모지 entity가 실제로 들어있는지 진단합니다.

    python -m scripts.inspect_template <template_id>
    python -m scripts.inspect_template            # id 없이 실행하면 최근 메시지 목록

출력에서 CustomEmoji 개수가 0이면, 그 메시지에는 애초에 커스텀 이모지가 entity로
들어있지 않은 것입니다(= 복사붙여넣기/작성 과정에서 깨진 것). 0보다 크면 우리 코드가
그대로 보존하는지(remap 전/후 개수)도 같이 보여줍니다.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telethon.tl.types import MessageEntityCustomEmoji

from raffle.client import build_client
from raffle.send import render_with_replacements
from raffle.state import load_state
from raffle.template import SAVED_MESSAGES, fetch_template


def summarize_entities(entities):
    counts = {}
    for e in entities or []:
        counts[type(e).__name__] = counts.get(type(e).__name__, 0) + 1
    return counts


async def inspect(client, template_id: int):
    template = await fetch_template(client, template_id)
    entities = template.entities or []
    custom = [e for e in entities if isinstance(e, MessageEntityCustomEmoji)]

    print("=" * 60)
    print(f"template_id = {template_id}")
    print(f"본문: {template.message!r}")
    print(f"entity 총 개수: {len(entities)}")
    print(f"entity 종류별: {summarize_entities(entities)}")
    print(f"커스텀(프리미엄) 이모지 개수: {len(custom)}")
    for e in custom:
        print(f"  - CustomEmoji offset={e.offset} length={e.length} document_id={e.document_id}")

    if not custom:
        print(
            "\n⚠️ 이 메시지에는 커스텀 이모지 entity가 없습니다.\n"
            "   => 화면에는 커스텀처럼 보여도, 메시지 자체에는 기본 이모지로만 저장된 상태입니다.\n"
            "   복사붙여넣기 말고, 텔레그램 이모지 키보드에서 직접 프리미엄 이모지를 골라 입력한 뒤\n"
            "   다시 등록해 보세요."
        )
        return

    # remap을 거쳐도 커스텀 이모지가 그대로 살아있는지 확인
    state = load_state()
    placeholder = state.get("placeholder", "@태그")
    _, new_entities = render_with_replacements(
        template, {placeholder: {"text": "@winner", "entity": None}}
    )
    new_custom = [e for e in new_entities if isinstance(e, MessageEntityCustomEmoji)]
    print(f"\nremap 후 커스텀 이모지 개수: {len(new_custom)} (전: {len(custom)})")
    if len(new_custom) == len(custom):
        print("✅ 우리 코드는 커스텀 이모지를 그대로 보존합니다. 프리미엄 계정이면 발송 시에도 유지됩니다.")
    else:
        print("❌ remap 과정에서 일부 커스텀 이모지가 사라졌습니다. (코드 버그 — 알려주세요)")


async def main():
    client = build_client()
    await client.start()
    me = await client.get_me()
    print(f"로그인 계정: {me.first_name} / 프리미엄 = {bool(getattr(me, 'premium', False))}")

    if len(sys.argv) > 1:
        await inspect(client, int(sys.argv[1]))
    else:
        print("\n(template_id 미지정) 최근 저장된 메시지 목록:")
        async for msg in client.iter_messages(SAVED_MESSAGES, limit=20):
            n_custom = len(
                [e for e in (msg.entities or []) if isinstance(e, MessageEntityCustomEmoji)]
            )
            preview = (msg.message or "").replace("\n", " ")[:50]
            print(f"  id={msg.id:<8} customEmoji={n_custom:<3} text={preview}")
        print("\n자세히 보려면:  python -m scripts.inspect_template <id>")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
