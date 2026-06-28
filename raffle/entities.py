import copy
from typing import Callable, Optional, TypedDict

from telethon import helpers
from telethon.tl.types import TypeMessageEntity


class Replacement(TypedDict, total=False):
    text: str
    # (offset, length) -> entity, 치환된 구간에 새로 씌울 entity가 필요할 때만 지정
    entity: Optional[Callable[[int, int], TypeMessageEntity]]


def remap_entities(
    raw_text: str,
    raw_entities: Optional[list],
    replacements: dict[str, Replacement],
) -> tuple[str, list]:
    """템플릿 원문에서 placeholder 토큰을 치환하면서, 나머지 entity(커스텀 이모지,
    굵게, 링크 등)의 offset/length를 그대로 보존(필요시 이동)합니다.

    Telegram entity의 offset/length는 UTF-16 코드 유닛 단위이기 때문에,
    Python 문자열 길이와 그대로 비교하면 이모지/한글 조합 등에서 어긋날 수 있습니다.
    Telethon의 add_surrogate/del_surrogate로 변환한 좌표계에서만 연산합니다.
    """
    text = helpers.add_surrogate(raw_text)
    entities = raw_entities or []

    spans = []
    for token, spec in replacements.items():
        idx = text.find(helpers.add_surrogate(token))
        if idx < 0:
            continue
        spans.append(
            {
                "start": idx,
                "end": idx + len(helpers.add_surrogate(token)),
                "new_text": helpers.add_surrogate(spec["text"]),
                "entity_factory": spec.get("entity"),
            }
        )
    spans.sort(key=lambda sp: sp["start"])

    parts: list[str] = []
    cursor = 0
    inserted_entities = []
    span_shifts = []  # (orig_start, orig_end, len_diff)

    for sp in spans:
        parts.append(text[cursor : sp["start"]])
        new_offset = sum(len(p) for p in parts)
        parts.append(sp["new_text"])
        new_length = len(sp["new_text"])
        if sp["entity_factory"]:
            inserted_entities.append(sp["entity_factory"](new_offset, new_length))
        span_shifts.append((sp["start"], sp["end"], new_length - (sp["end"] - sp["start"])))
        cursor = sp["end"]
    parts.append(text[cursor:])
    new_text = "".join(parts)

    def delta_before(offset: int) -> int:
        return sum(diff for (_, end, diff) in span_shifts if end <= offset)

    kept_entities = []
    for ent in entities:
        o, l = ent.offset, ent.length
        contained_diff = 0
        drop = False
        for start, end, diff in span_shifts:
            fully_before_or_after = end <= o or start >= o + l
            fully_contains = o <= start and end <= o + l
            if fully_before_or_after:
                continue
            if fully_contains:
                contained_diff += diff
                continue
            # placeholder가 entity와 부분적으로만 겹치는 예외적인 경우: 보존하지 않음
            drop = True
            break
        if drop:
            continue
        new_ent = copy.copy(ent)
        new_ent.offset = o + delta_before(o)
        new_ent.length = l + contained_diff
        kept_entities.append(new_ent)

    kept_entities.extend(inserted_entities)
    kept_entities.sort(key=lambda e: e.offset)

    return helpers.del_surrogate(new_text), kept_entities
