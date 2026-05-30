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

Current implementation status:

- Common agent input/output dataclasses: done
- Chief Investment Agent orchestration: done
- Deterministic Market Analysis Agent stub: done
- Stock Recommendation Agent for one-symbol universe: done
- Trading Strategy Agent candidate ticket generation: done
- Risk Management Agent policy checks: done
- Paper Trade Execution Agent: done
- Telegram-ready report text: initial CLI report done
- SQLite decision-trail persistence: agent run, trade ticket, risk review done

Verification:

```bash
python3 -m app.main
python3 -m unittest discover -s tests
```

Expected result: CLI prints a Chief Investment Agent report and the test suite passes.

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
