"""저장된 메시지(Saved Messages) 최근 N개를 id와 미리보기로 출력합니다.
템플릿으로 쓸 메시지의 id를 찾을 때 사용하세요.

    python -m scripts.list_saved_templates [limit]
"""
import asyncio
import sys

from raffle.client import build_client
from raffle.template import SAVED_MESSAGES


async def main(limit: int):
    client = build_client()
    await client.start()
    async for msg in client.iter_messages(SAVED_MESSAGES, limit=limit):
        preview = (msg.message or "").replace("\n", " ")[:60]
        n_entities = len(msg.entities or [])
        print(f"id={msg.id:<8} entities={n_entities:<3} text={preview}")
    await client.disconnect()


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    asyncio.run(main(limit))
