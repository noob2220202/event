# 이벤트 추첨봇 (유저 세션 기반)

Bot API 토큰이 아니라, 실제 텔레그램 계정으로 로그인하는 "유저 세션"(Telethon, MTProto)으로
동작하는 추첨/이벤트 발송 도구입니다.

## 왜 봇이 아니라 유저 세션인가

프리미엄 커스텀 이모지는 메시지에 `custom_emoji_id`를 가진 entity로 붙어 있습니다. 이 entity를
새로 만들어서 보내는 것보다, **이미 잘 꾸며진 메시지(저장된 메시지)의 원본 text+entities를 그대로
재사용하면서 태그 부분만 치환**하는 방식이 가장 안전하고 깨질 일이 없습니다. 이를 위해서는 본인 계정의
"저장된 메시지(Saved Messages)"에 직접 접근해야 하는데, 이건 Bot API로는 할 수 없고 유저 세션으로만
가능합니다.

```
저장된 메시지에 작성한 템플릿(프리미엄 이모지 + 서식 + "@태그" placeholder)
        │  (원본 text, entities 그대로 읽음)
        ▼
   placeholder만 실제 멘션으로 치환 (다른 entity는 offset만 보정해서 보존)
        ▼
   대상 채팅으로 전송
```

> ⚠️ **주의**: 텔레그램 ToS는 "개인 계정을 봇처럼 자동화하는 것"을 금지합니다(자동화가 필요하면
> Bot API를 쓰라는 것이 공식 입장). 유저 세션으로 자동 발송을 하면 계정이 제한/정지될 위험이 있으니,
> 본인 책임 하에 과도하지 않은 빈도로만 사용하세요. 또한 `*.session` 파일은 계정 전체를 탈취할 수 있는
> 민감 정보이므로 절대 커밋/공유하지 마세요 (`.gitignore`에 이미 제외되어 있습니다).

## 설치

```bash
pip install -r requirements.txt
cp .env.example .env
```

[my.telegram.org](https://my.telegram.org)에서 `api_id`, `api_hash`를 발급받아 `.env`에 입력하세요.

## 사용 순서

### 1) 최초 로그인 (세션 생성)

```bash
python -m scripts.login
```

전화번호 → 텔레그램으로 받은 인증코드 → (2단계 인증이 켜져 있다면) 비밀번호를 입력하면
`<TG_SESSION_NAME>.session` 파일이 생성됩니다. 이후 스크립트는 모두 이 세션을 재사용합니다.

### 2) 템플릿 작성

본인 텔레그램 앱에서 **저장된 메시지(Saved Messages)** 를 열고, 원하는 만큼 화려하게 꾸민 메시지를
작성합니다. 프리미엄 커스텀 이모지, 굵게, 색상 등 자유롭게 사용하고, 태그가 들어갈 자리에는
`@태그` 라는 문자열을 그대로 입력해두세요 (다른 placeholder를 쓰고 싶으면 `--placeholder` 옵션으로
바꿀 수 있습니다).

### 3) 템플릿 메시지 id 확인

```bash
python -m scripts.list_saved_templates
```

최근 저장된 메시지들의 `id`, entity 개수, 미리보기가 출력됩니다. 사용할 템플릿의 `id`를 기억해두세요.

### 4) 발송

```bash
python -m scripts.draw_winner \
  --template-id 123 \
  --chat @my_event_channel \
  --user @winner_username \
  --dry-run
```

`--dry-run`으로 치환된 결과(텍스트 + entity 목록)를 먼저 확인하고, 문제없으면 `--dry-run`을 빼고
실제로 전송하세요.

- `--user`는 `@username` 또는 user_id 모두 가능합니다. username이 없는 유저는 표시 이름으로
  text-mention(MessageEntityMentionName) 처리되어 클릭 시 그 유저를 핑(ping)합니다.
- `{{COUNT}}=5668명` 처럼 `--extra`를 여러 번 줘서 참가자 수 등 다른 placeholder도 같이 치환할 수
  있습니다.

## 동작 원리 (entity 보존)

`raffle/entities.py`의 `remap_entities`가 핵심입니다. 텔레그램 entity의 `offset`/`length`는
**UTF-16 코드 유닛** 단위라서, 이모지처럼 서로게이트 페어로 표현되는 문자가 끼어 있으면 Python
문자열 길이와 어긋납니다. Telethon의 `add_surrogate`/`del_surrogate`로 좌표계를 맞춘 뒤:

1. placeholder 토큰의 위치를 찾고
2. 치환 텍스트 길이만큼 이후 entity들의 offset을 보정하고
3. placeholder를 완전히 감싸는 entity(예: 전체 굵게)는 length만 보정해서 그대로 유지하고
4. placeholder 내부에만 걸려있던 entity(예: placeholder 글자에만 적용된 서식)는 제거하고
5. 새 멘션 entity를 그 자리에 추가합니다.

그 결과 커스텀 이모지·서식 등 나머지 꾸밈은 그대로 보존되고, 태그 자리만 실제 유저로 바뀝니다.

## 알아두면 좋은 제약

- `client.get_entity(...)`로 유저를 찾으려면 세션이 그 유저를 이미 한 번이라도 본 적이 있어야
  합니다(같은 그룹에 있거나, 메시지를 주고받은 적이 있는 등). 완전히 모르는 raw user_id는 access hash가
  없어 바로 조회되지 않을 수 있습니다 — 보통 추첨 대상 채팅의 참가자/메시지 작성자 목록에서 가져오면
  문제없습니다.
- 과도하게 빠른 반복 발송은 플러드 제한(FloodWaitError)에 걸릴 수 있습니다.
