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
- Account State aware risk shrinking/rejection: done
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

Goal: 키움 REST API 인증, 계좌 조회, 현재가 조회를 붙인다.

Current implementation status:

- Environment settings loader: done (`app/config/settings.py`)
- Safe `.env.example`: done
- Kiwoom auth/client/market/account skeleton: done
- Transport-injected tests without real credentials: done
- Manual read-check script: done (`scripts/check_kiwoom_read_api.py`)

User-required blocker before real API verification:

- Fill local `.env` with real Kiwoom REST API credentials. Do not commit `.env`.

Manual verification after credentials are available:

```bash
cp .env.example .env
# edit .env with real KIWOOM_APP_KEY, KIWOOM_SECRET_KEY, KIWOOM_ACCOUNT_NO
python3 scripts/check_kiwoom_read_api.py
```

Expected result: token is issued, `498270` current price is printed, account balance is printed.

## MVP 3 — Telegram Approval Flow

Approval command text 생성, `승인 TT-...` / `거절 TT-...` 파싱, ticket status 업데이트, execution result 알림.

Current implementation status:

- Korean approval/rejection parser: done
- Ticket user approval/rejection status update: done
- Paper-mode approval execution: done
- CLI handler script for Telegram text payload simulation: done
- Actual Telegram gateway webhook/update binding: done
- Scheduled scan Telegram notification text: done

## MVP 4 — live_manual Order Execution

`ENABLE_LIVE_TRADING=true`, `TRADING_MODE=live_manual`, risk approved, user approved, allowed symbol 조건에서만 실행.

Current implementation status:

- Dry-run order request preparation: done
- Final approval command: done
- `order_events` live-order audit log: done
- Live disabled hard gate before broker order API: done

## MVP 5 — Limited Auto Trading

Small order amount, whitelist symbols, cooldown, daily loss cap, circuit breaker.

Current implementation status:

- Scheduler-safe one-shot scan script: done
- KST market scan window guard: done
- Weekend/configured KRX holiday skip: done
- Telegram alert for pending approval ticket: done
- Runtime circuit breaker state: done
- Order cooldown enforcement before scheduled scans: done
- Daily executed-buy amount guard before scheduled scans: done
- Scheduler/cron quiet wrapper: done
- Dynamic KRX/Korea holiday calendar with cache fallback: done
- Daily realized-loss guard from real fill/position state: done
- Post-fill circuit breaker automation: done

Remaining:

- MVP 6 post-trade analysis loop

## MVP 6 — Post-Trade Analysis Loop

체결 이후 사후 분석을 통해 전략 개선점을 저장한다.

Current implementation status:

- Ticket/run/order event/realized P&L based post-trade analysis: done
- `post_trade_analyses` persistence: done
- CLI report generation: done (`scripts/analyze_trade_ticket.py`)

Remaining:

- Daily Telegram post-trade digest
- Strategy improvement memory/export loop
