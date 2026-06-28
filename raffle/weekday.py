KOREAN_WEEKDAYS = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
ENGLISH_WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
WEEKDAY_NAMES_KO = ["월", "화", "수", "목", "금", "토", "일"]


def parse_weekday(token: str) -> int:
    """'일', '일요일', 'sun', 'Sunday' 등을 0(월)~6(일) 인덱스로 변환합니다."""
    token = token.strip()
    if token.endswith("요일"):
        token = token[: -len("요일")]
    if token in KOREAN_WEEKDAYS:
        return KOREAN_WEEKDAYS[token]
    key = token[:3].lower()
    if key in ENGLISH_WEEKDAYS:
        return ENGLISH_WEEKDAYS[key]
    raise ValueError(f"요일을 인식할 수 없습니다: {token!r} (예: 월,화,수,목,금,토,일)")
