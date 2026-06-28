"""최초 1회 실행: 전화번호/인증코드/2단계 비밀번호를 입력해 유저 세션을 생성합니다.

    python -m scripts.login
"""
import asyncio

from raffle.client import build_client


async def main():
    client = build_client()
    await client.start()
    me = await client.get_me()
    print(f"로그인 완료: {me.first_name} (@{me.username or me.id})")
    print("세션 파일이 저장되었습니다. 이후 스크립트들은 이 세션을 그대로 사용합니다.")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
