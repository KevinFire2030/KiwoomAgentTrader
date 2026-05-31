# Kiwoom Agent Trader

키움증권 REST API를 도구로 사용하는 **멀티 에이전트 기반 투자 의사결정 및 거래 실행 시스템**입니다.

## 핵심 컨셉

단순 Python 자동매매 스크립트가 아니라, 역할과 권한이 분리된 에이전트들이 투자 의사결정 과정을 수행하는 구조를 목표로 합니다.

```text
시장 분석 → 종목 추천 → 매매 전략 → 리스크 심사 → 거래 실행 → 사후 분석
```

## MVP 목표

1차 MVP는 `498270 KIWOOM 미국양자컴퓨팅 ETF`를 대상으로 멀티 에이전트 회의, Trade Ticket 생성, 리스크 정책 심사, paper mode 주문 기록, 텔레그램 승인 요청 리포트 생성을 수행합니다.

## 안전 원칙

- 실거래는 기본 OFF
- 주문 권한은 Trade Execution Agent에만 부여
- Risk Management Agent 승인 없는 주문 금지
- live_manual 전까지 키움 주문 API 호출 금지
- live_manual에서도 `ENABLE_LIVE_TRADING=true` 없이는 주문 API 제출 금지
- 모든 판단과 주문은 로그/DB에 저장

## 문서

- [Agent Architecture](docs/agent-architecture.md)
- [Safety Design](docs/safety-design.md)
- [MVP Roadmap](docs/mvp-roadmap.md)
- [Conversation Log](docs/conversation-log.md)

## 로컬 실행

```bash
python3 -m app.main
python3 -m unittest discover -s tests
```

## 키움 REST API 읽기 검증

`.env`를 채운 뒤 아래 명령으로 토큰 발급, 현재가 조회, 계좌 잔고 조회를 확인합니다. 계좌번호는 출력에서 마스킹됩니다.

```bash
python3 scripts/check_kiwoom_read_api.py
```

## 최근 1년 입출금 내역 조회

키움 `kt00015` 위탁종합거래내역요청으로 최근 1년 이내 입출금 내역을 조회하고 입금/출금 합계와 마지막 예수금잔고를 요약합니다.

```bash
python3 scripts/check_kiwoom_deposit_withdraw_history.py
```

## 실제 읽기 데이터 기반 에이전트 workflow

아래 명령은 키움 REST API에서 `498270` 현재가, 계좌 snapshot, 최근 1년 입출금 내역을 가져온 뒤 Chief Investment Agent workflow에 주입합니다. 현재 구현은 `paper` 모드에서만 주문 기록을 남기며, 실주문 API는 호출하지 않습니다.

```bash
python3 scripts/run_kiwoom_intraday_workflow.py 498270
```

Account State Agent는 다음 값을 계산해 Chief Agent 리포트와 DB에 남깁니다.

- 현금성 잔고
- 보유 평가금액과 보유종목 수
- 최근 1년 입금/출금/순입금
- MVP 기준 투자 가능 현금: 현금성 잔고의 30%

Risk Management Agent는 Account State를 사용해 다음 안전 규칙을 적용합니다.

- 투자 가능 현금을 초과하는 매수 티켓은 가능한 수량으로 자동 축소
- 투자 가능 현금으로 1주도 매수할 수 없으면 리스크 거절
- 최근 1년 출금액이 입금액보다 크면 `medium` 리스크로 보수적 표시
- 1회 주문 최대 금액 한도 초과 시 수량 축소 또는 거절

## Telegram 승인/거절 명령 처리

생성된 리스크 승인 티켓은 Telegram 명령 형식으로 승인/거절할 수 있습니다.

```bash
python3 scripts/handle_approval_command.py '승인 TT-...'
python3 scripts/handle_approval_command.py '거절 TT-...'
```

현재 `paper` 모드에서는 승인된 티켓만 `paper_executed` 상태로 바뀌고, 실제 키움 주문 API는 호출하지 않습니다.

## Telegram Gateway 실제 연결

Telegram 메시지 update를 approval workflow에 직접 연결할 수 있습니다. 대상 채팅/토픽은 `.env`에 고정해 다른 방의 명령이 실행되지 않게 합니다.

```bash
TELEGRAM_BOT_TOKEN=...
KIWOOM_TELEGRAM_CHAT_ID=-100...
KIWOOM_TELEGRAM_THREAD_ID=502
KIWOOM_TRADING_DB=data/trading.db
```

Webhook/update JSON 1건 처리:

```bash
cat telegram_update.json | python3 scripts/handle_telegram_approval_update.py --send
```

전용 봇으로 long polling bridge 실행:

```bash
python3 scripts/run_telegram_approval_bridge.py --mode paper
```

주의: 동일 Bot token을 Hermes Gateway가 이미 polling 중이면 Telegram `getUpdates` long polling은 한 프로세스만 사용하세요. Hermes Gateway와 병행 운영할 때는 webhook/update JSON 진입점 또는 전용 승인 봇 token을 사용합니다.

## 정기 스캔/Telegram 알림

장 시간에만 1회 스캔을 실행하고, 결과를 Telegram 승인 토픽으로 보낼 수 있습니다. 기본 장 시간은 KST `09:05`~`15:10`이며, 주말과 `.env`의 `KRX_HOLIDAYS` 날짜는 자동 생략합니다.

```bash
python3 scripts/run_scheduled_kiwoom_scan.py --no-send
python3 scripts/run_scheduled_kiwoom_scan.py 498270
scripts/cron_kiwoom_scan.sh
```

환경 변수:

```bash
KIWOOM_SCAN_SYMBOL=498270
KIWOOM_SCAN_FORCE=false
KIWOOM_NOTIFY_WHEN_NO_TICKET=true
KIWOOM_ENFORCE_OPERATIONAL_RISK=true
KIWOOM_CIRCUIT_BREAKER_ENABLED=true
MAX_DAILY_BUY_AMOUNT_KRW=300000
MAX_DAILY_LOSS_KRW=50000
KRX_HOLIDAY_SOURCE=auto
KRX_HOLIDAY_CACHE_DIR=data/calendar
KRX_HOLIDAY_YEARS=
KRX_HOLIDAYS=2026-01-01,20260216
```

동작:

- 장 시간 밖이면 workflow를 실행하지 않고 생략 메시지만 출력합니다.
- `KRX_HOLIDAY_SOURCE=auto`는 한국 공휴일 API를 조회해 `data/calendar/kr_holidays_YYYY.json`에 캐시하고, 실패 시 캐시/수동 `KRX_HOLIDAYS`로 fallback합니다.
- 휴장일 로더 검증은 `python3 scripts/check_krx_holidays.py --year 2026`로 할 수 있습니다.
- `--force` 또는 `KIWOOM_SCAN_FORCE=true`이면 장 시간 밖에서도 강제 실행할 수 있습니다.
- 운영 리스크 가드가 켜져 있으면 circuit breaker, 주문 cooldown, 일일 매수 한도, 일일 실현손실 한도를 먼저 검사합니다.
- 실현손익은 `realized_pnl_events`에 저장된 실제 체결/포지션 동기화 결과를 KST 당일 기준으로 합산합니다. 당일 합계가 `-MAX_DAILY_LOSS_KRW` 이하이면 신규 스캔을 차단합니다.
- 티켓이 생성되면 알림에 `승인 TT-...` / `거절 TT-...` 명령이 포함됩니다.
- `--no-send`는 Telegram API 호출 없이 알림 텍스트만 검증합니다.
- `scripts/cron_kiwoom_scan.sh`는 scheduler용 wrapper이며, 장외/휴장/알림 없음/전송 성공 시 stdout을 비워 cron 알림 스팸을 막습니다.

운영 circuit breaker는 아래 스크립트로 확인/변경합니다.

```bash
python3 scripts/manage_runtime_risk.py status
python3 scripts/manage_runtime_risk.py on --reason "manual halt"
python3 scripts/manage_runtime_risk.py off --reason "resume scans"
```

체결/포지션 동기화 후 실현손익 이벤트를 기록하면 post-fill circuit breaker가 즉시 적용됩니다. 당일 실현손익 합계가 `-MAX_DAILY_LOSS_KRW` 이하이면 `runtime_state.circuit_breaker=on`으로 전환되어 이후 정기 스캔이 자동 차단됩니다.

```bash
python3 scripts/record_realized_pnl_event.py \
  --symbol 498270 \
  --realized-pnl -55000 \
  --source kiwoom_fill_sync
```

키움 read endpoint에서 가져온 거래/체결 후보 row를 기반으로 실현손익 이벤트를 동기화할 수 있습니다. 기본은 `--dry-run`이며, `--apply`를 명시해야 DB에 raw broker snapshot과 derived `realized_pnl_events`가 저장됩니다. dedupe key를 사용해 반복 실행 중복 기록을 방지합니다.

```bash
python3 scripts/sync_kiwoom_fills.py --dry-run
python3 scripts/sync_kiwoom_fills.py --apply
```

개장 직전/직후 read-only 리허설은 아래 명령으로 상태 확인, Kiwoom read API, paper scan, fill sync dry-run을 순서대로 실행합니다. 이 명령은 Kiwoom 주문 API를 호출하지 않습니다.

```bash
python3 scripts/run_market_open_rehearsal.py
```

사후 분석은 티켓, risk review, 주문 이벤트, `realized_pnl_events`를 연결해 리포트와 개선 메모를 생성하고 `post_trade_analyses`에 저장합니다. 손익 이벤트의 raw JSON에 `ticket_id`가 들어 있으면 해당 티켓 분석에 연결됩니다.

```bash
python3 scripts/analyze_trade_ticket.py TT-...
```

일일 사후 분석 digest는 KST 날짜 기준으로 `post_trade_analyses`를 집계해 총 실현손익, win/loss/flat 개수, 최고/최저 티켓, 주요 개선 메모, 현재 circuit breaker 상태를 Telegram 전송용 텍스트로 생성합니다.

```bash
python3 scripts/send_daily_post_trade_digest.py --date 2026-06-01 --no-send
python3 scripts/send_daily_post_trade_digest.py --date 2026-06-01
```

`--no-send`는 Telegram Bot API를 호출하지 않고 출력만 검증합니다. 실제 전송 시 `TELEGRAM_BOT_TOKEN`, `KIWOOM_TELEGRAM_CHAT_ID` 또는 `TELEGRAM_CHAT_ID`, 선택적으로 `KIWOOM_TELEGRAM_THREAD_ID`가 필요합니다.

누적 전략 개선 메모는 `post_trade_analyses`의 lessons를 KST 날짜/심볼/결과별로 묶어 `docs/strategy-lessons.md`에 내보냅니다. 생성 블록은 marker로 관리되어 기존 수동 메모를 보존하고, 각 lesson에는 source ticket ID가 남습니다.

```bash
python3 scripts/export_strategy_lessons.py
python3 scripts/export_strategy_lessons.py --output docs/strategy-lessons.md
```

자동화 상태 명령은 로컬 DB와 artifact만 읽어 현재 운영 준비 상태를 요약합니다. trading mode/live gate, 최신 snapshot 시각, circuit breaker, 승인 대기 티켓, 사후 분석/전략 메모 상태를 보여주며 Kiwoom 주문 API는 호출하지 않습니다.

```bash
python3 scripts/show_automation_status.py
python3 scripts/show_automation_status.py --symbol 498270
```

## live_manual 주문 API 준비

`live_manual` 모드에서 사용자 승인까지 끝난 티켓은 즉시 실주문을 내지 않고 `live_manual_ready` 상태로 전환됩니다. 주문 요청 payload는 dry-run 스크립트로 확인할 수 있습니다.

```bash
python3 scripts/prepare_live_order_request.py TT-...
```

이 스크립트는 키움 주문 API를 호출하지 않고, `/api/dostk/ordr` 요청 endpoint/api-id/payload만 출력합니다. 실제 주문 제출은 별도 `ENABLE_LIVE_TRADING=true` 게이트가 켜져야 하며, 기본값은 항상 OFF입니다.

## live_manual 최종승인과 주문 감사 로그

`live_manual_ready` 티켓은 2단계 명령으로만 제출 경로에 들어갑니다.

```bash
python3 scripts/handle_final_approval_command.py '최종승인 TT-...'
```

안전 동작:

- `TRADING_MODE=live_manual` 그리고 `ENABLE_LIVE_TRADING=true`가 아니면 키움 주문 API를 호출하지 않습니다.
- 차단/제출/브로커 거절 결과는 모두 `order_events`에 저장합니다.
- 저장 항목은 `ticket_id`, `mode`, `event_type`, `status`, 주문 요청 JSON, 브로커 응답 JSON, 메시지입니다.

저장되는 데이터:

- `market_snapshots`: 현재가, 등락률, 원본 응답 JSON
- `account_snapshots`: 마스킹 계좌번호, 예수금/추정자산, 평가금액, 보유종목 수
- `account_states`: Account State Agent가 계산한 현금흐름/투자 가능 현금
- `agent_runs`, `trade_tickets`, `risk_reviews`: 에이전트 판단/리스크 심사 이력
