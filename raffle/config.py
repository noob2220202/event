import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    api_id: int
    api_hash: str
    session_name: str


def load_settings() -> Settings:
    api_id = os.environ.get("TG_API_ID")
    api_hash = os.environ.get("TG_API_HASH")
    session_name = os.environ.get("TG_SESSION_NAME", "raffle_user")

    if not api_id or not api_hash:
        raise RuntimeError(
            "TG_API_ID / TG_API_HASH 환경변수가 없습니다. "
            ".env.example을 .env로 복사하고 my.telegram.org에서 발급받은 값을 채워주세요."
        )

    return Settings(api_id=int(api_id), api_hash=api_hash, session_name=session_name)
