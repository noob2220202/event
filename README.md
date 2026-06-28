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

## 전체 구조

상시 실행되는 프로세스가 두 개입니다 (pm2로 관리, 로그인만 예외).

```
scripts/login.py       (1회성, 대화형 — pm2 대상 아님)
        │ 세션 생성
        ▼
scripts/registrar.py   (pm2) — 저장된 메시지의 /1 /2 /chat ... 명령을 듣고 data/state.json에 등록
scripts/scheduler.py   (pm2) — data/state.json을 주기적으로 읽어 매주 정해진 요일/시각에 발송
```

`data/state.json`이 둘 사이의 유일한 공유 상태입니다. 등록(registrar)과 발송(scheduler)이 서로
직접 통신하지 않고, 파일을 통해서만 동기화되기 때문에 한쪽을 pm2로 재시작해도 다른 쪽에 영향이 없습니다.

## 사용 순서

### 1) 최초 로그인 (세션 생성, pm2 아님)

```bash
python -m scripts.login
```

전화번호 → 텔레그램으로 받은 인증코드 → (2단계 인증이 켜져 있다면) 비밀번호를 입력하면
`<TG_SESSION_NAME>.session` 파일이 생성됩니다. 이후 모든 프로세스가 이 세션을 재사용합니다.
대화형 입력이 필요하므로 pm2로 실행하지 마세요.

### 2) registrar / scheduler를 pm2로 기동

```bash
npm install -g pm2   # 이미 있으면 생략
pm2 start ecosystem.config.js
pm2 logs             # 동작 확인
pm2 save             # 서버 재부팅 시에도 유지하려면
```

`ecosystem.config.js`의 `interpreter`는 기본값이 `python3`입니다. venv를 쓴다면 venv의 python
경로(예: `./venv/bin/python3`)로 바꿔주세요.

### 3) 텔레그램에서 템플릿 작성 + 등록

본인 텔레그램 앱에서 **저장된 메시지(Saved Messages)** 를 열고, 단계별로 원하는 만큼 화려하게
꾸민 메시지를 각각 작성합니다 (1시간 전 공지, 10분 전 공지, 추첨 중, 당첨자 발표 등). 프리미엄
커스텀 이모지, 굵게, 색상 등 자유롭게 쓰고, **당첨자를 태그할 메시지에만** 그 자리에 `@태그`
문자열을 그대로 입력해두세요. (다른 placeholder를 쓰고 싶으면 `/placeholder` 명령으로 바꿀 수
있습니다.)

각 템플릿 메시지에 **답장(reply)** 으로 아래 명령을 보내 등록합니다:

```
/<단계번호> <요일> <HH:MM>
```

예)

```
/1 일 18:00     ← "1시간 전" 템플릿에 답장
/2 일 18:50     ← "10분 전" 템플릿에 답장
/3 일 19:00     ← "추첨 중" 템플릿에 답장
/4 일 19:01     ← "당첨자 발표"(@태그 포함) 템플릿에 답장
```

등록되면 registrar가 같은 자리에 ✅ 확인 답장을 보냅니다. 이후 매주 일요일 그 시각에 scheduler가
자동으로 발송합니다 (state.json 변경은 최대 30초 내 scheduler에 반영됩니다).

대상 채팅과 placeholder도 저장된 메시지에서 명령으로 설정합니다 (답장 아니어도 됨):

| 명령 | 설명 |
|---|---|
| `/<n> <요일> <HH:MM>` (답장 필수) | n단계 템플릿 + 매주 발송 요일/시각 등록 |
| `/del <n>` | n단계 등록 삭제 |
| `/chat <대상>` | 발송 대상 채팅 설정, 예) `/chat @my_event_channel` |
| `/placeholder <문자열>` | 당첨자 태그 placeholder 변경 (기본값 `@태그`) |
| `/list` | 현재 등록 상태(대상 채팅, placeholder, 단계 목록) 확인 |
| `/help` | 명령어 도움말 |

요일은 `월 화 수 목 금 토 일` (또는 `월요일`처럼 풀네임, `mon/sun` 등 영문 약어)을 모두 인식합니다.

### 4) 당첨자 발표는 자동

scheduler는 발송 직전, 그 단계 템플릿 안에 placeholder(`@태그`)가 들어있는지 검사합니다.
들어있으면 `/chat`으로 설정한 대상 채팅의 참여자 중 **봇을 제외하고 무작위로 한 명**을 뽑아 그
자리에 태그해서 보냅니다. placeholder가 없는 일반 공지 단계는 그대로 발송됩니다.

### 수동/테스트 발송 (선택)

스케줄과 무관하게 즉시 한 번 보내보고 싶을 때는 기존 CLI를 그대로 쓸 수 있습니다.

```bash
python -m scripts.list_saved_templates           # 템플릿 id 확인
python -m scripts.draw_winner \
  --template-id 123 \
  --chat @my_event_channel \
  --user @winner_username \
  --dry-run
```

`--dry-run`으로 치환된 결과(텍스트 + entity 목록)를 먼저 확인하고, 문제없으면 `--dry-run`을 빼고
실제로 전송하세요.

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
- 당첨자 추첨(`raffle/winner.py`)은 `get_participants`로 대상 채팅의 **멤버 목록**을 가져옵니다.
  참여자가 매우 많은 대형 채널/그룹이거나, 멤버 목록 조회 권한이 없는 채널이면 느리거나 실패할 수
  있습니다.
- scheduler는 `data/state.json`을 메모리 잡 스토어로만 스케줄링합니다. pm2가 scheduler 프로세스를
  재시작하는 그 순간에 정확히 걸쳐있던 발송 한 번은 건너뛸 수 있습니다(다음 주는 정상 발송).
  안정성이 중요하면 pm2 로그(`pm2 logs raffle-scheduler`)로 발송 여부를 확인하세요.
- 과도하게 빠른 반복 발송은 플러드 제한(FloodWaitError)에 걸릴 수 있습니다.
- `data/state.json`은 운영 중 계속 바뀌는 상태 파일이라 git에서 제외했습니다(`data/state.example.json`
  참고). 서버를 옮기거나 백업할 때는 이 파일도 같이 챙기세요.
