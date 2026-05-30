# Kiwoom Agent Trader MVP Roadmap

## MVP 0 — Project Foundation

- 설계 문서 작성
- `E:/KiwoomAgentTrader` 프로젝트 폴더 생성
- GitHub 레포 연결 및 푸시
- 기본 `app/` 스캐폴딩
- 정책 YAML 작성
- 초기 테스트 작성

## MVP 1 — Paper Mode Multi-Agent Meeting

Goal: `498270` ETF를 대상으로 에이전트 회의 결과를 생성하고 paper Trade Ticket을 기록한다.

Tasks:

1. Define common agent input/output dataclasses.
2. Implement Chief Investment Agent orchestration.
3. Implement deterministic Market Analysis Agent stub.
4. Implement Stock Recommendation Agent for one-symbol universe.
5. Implement Trading Strategy Agent that can create a candidate ticket.
6. Implement Risk Management Agent policy checks.
7. Implement Paper Trade Execution Agent.
8. Produce Telegram-ready report text.
9. Persist workflow result to SQLite.

Verification:

```bash
python3 -m app.main
python3 -m unittest discover -s tests
```

## MVP 2 — Kiwoom Read API Integration

Kiwoom auth client, account balance lookup, current price lookup for `498270`, market/account snapshot 저장.

## MVP 3 — Telegram Approval Flow

Approval command text 생성, `승인 TT-...` / `거절 TT-...` 파싱, ticket status 업데이트, execution result 알림.

## MVP 4 — live_manual Order Execution

`ENABLE_LIVE_TRADING=true`, `TRADING_MODE=live_manual`, risk approved, user approved, allowed symbol 조건에서만 실행.

## MVP 5 — Limited Auto Trading

Small order amount, whitelist symbols, cooldown, daily loss cap, circuit breaker.

## MVP 6 — Post-Trade Analysis Loop

체결 이후 사후 분석을 통해 전략 개선점을 저장한다.
