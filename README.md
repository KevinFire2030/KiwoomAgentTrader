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
