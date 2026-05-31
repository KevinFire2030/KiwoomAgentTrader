# KiwoomAgentTrader Implementation Handoff

Last updated: 2026-06-01
Thread: Telegram group `hermes`, topic/thread 502
Repository: `/mnt/e/KiwoomAgentTrader`

## Current repo state

- Branch: `main`
- Remote: `origin/main`
- Latest checked state before this handoff: clean worktree, synced with origin.
- Recent feature commit to know: `37fd178 feat: add post-trade analysis loop`
- Subsequent docs transcript sync commits may appear after it.
- Latest full test result observed: `python3 -m unittest discover -s tests` → `Ran 69 tests ... OK`
- Latest Kiwoom read API smoke observed:
  - mode: `paper`
  - masked account: `63***96`
  - current price read for `498270`: OK
  - account balance read: OK
- Live order API remains guarded/disabled by default. Do not enable live trading without explicit user action.

## Implementation completion estimate

- PoC/MVP implementation: about 95% complete.
- Semi-auto practical operation: about 88–90% complete.
- Fully automatic `live_auto`: about 75–80% complete, intentionally not opened.

The current bottleneck is not architecture but finishing daily reporting/export loops and later hardening real fill/position sync.

## Implemented so far

### MVP 0 — Project foundation

- Project repository created at `/mnt/e/KiwoomAgentTrader`.
- Basic `app/`, `scripts/`, `tests/`, `docs/` structure exists.
- Roadmap and safety docs exist.
- GitHub remote is connected and pushes have succeeded.

### MVP 1 — Paper mode multi-agent meeting

Implemented:

- Common agent dataclasses.
- Chief Investment Agent orchestration.
- Deterministic Market Analysis Agent stub.
- Stock Recommendation Agent for `498270` universe.
- Trading Strategy Agent candidate ticket generation.
- Risk Management Agent policy checks.
- Account State aware risk shrinking/rejection.
- Paper Trade Execution Agent.
- Telegram-ready report text.
- SQLite decision trail for runs, tickets, risk reviews.

Important files:

- `app/agents/`
- `app/workflows/intraday_signal_scan.py`
- `app/main.py`
- `tests/test_workflow.py`
- `tests/test_chief_agent.py`
- `tests/test_risk_policy.py`

### MVP 2 — Kiwoom read API integration

Implemented:

- `.env`/settings loader.
- Kiwoom auth/client/market/account skeleton.
- Real Kiwoom read API verification script.
- Transport-injected tests without real credentials.
- Market/account snapshots integrated into workflow input.
- Transaction history read support via `kt00015`.
- Account State Agent using account/transaction history.

Important files:

- `app/config/settings.py`
- `app/config/dotenv.py`
- `app/kiwoom/auth.py`
- `app/kiwoom/client.py`
- `app/kiwoom/market.py`
- `app/kiwoom/account.py`
- `app/kiwoom/transactions.py`
- `app/kiwoom/snapshots.py`
- `app/agents/account_state.py`
- `scripts/check_kiwoom_read_api.py`
- `tests/test_kiwoom_clients.py`
- `tests/test_kiwoom_snapshots.py`
- `tests/test_kiwoom_transaction_history.py`
- `tests/test_account_state_agent.py`

Notes:

- Kiwoom token response may use `token`, not `access_token`.
- Kiwoom REST calls often use POST + `api-id` header.
- For `kt00015` recent 1-year transaction requests, avoid inclusive `today - 365 days` through `today`; use `today.replace(year=today.year - 1) + timedelta(days=1)`.

### MVP 3 — Telegram approval flow

Implemented:

- Korean approval/rejection parser.
- Commands like `승인 TT-...`, `거절 TT-...`.
- Ticket status update for user approval/rejection.
- Paper-mode approval execution.
- CLI simulation handler.
- Telegram gateway/webhook/update binding.
- Telegram topic allowlist/idempotency protections.
- Scheduled scan Telegram notification text.

Important files:

- `app/approval/commands.py`
- `app/approval/workflow.py`
- `app/telegram/approval_gateway.py`
- `app/telegram/client.py`
- `scripts/handle_telegram_approval_command.py`
- `scripts/run_telegram_approval_bridge.py`
- `tests/test_approval_flow.py`
- `tests/test_telegram_approval_gateway.py`

Notes:

- If Hermes Gateway already owns Telegram polling for the bot, do not start a second `getUpdates` long-polling loop with the same token.
- Prefer webhook/update JSON entry point or a dedicated approval bot token if needed.

### MVP 4 — `live_manual` order execution preparation

Implemented:

- Dry-run live order request builder.
- `live_manual_ready` state after user approval.
- Final approval command path.
- `order_events` audit log.
- Live disabled hard gate before broker order API.
- Broker order submission path is still guarded by `TRADING_MODE=live_manual` and `ENABLE_LIVE_TRADING=true`.

Important files:

- `app/kiwoom/orders.py`
- `app/tools/kiwoom_order_tool.py`
- `scripts/prepare_live_order_request.py`
- `scripts/handle_final_approval_command.py`
- `tests/test_kiwoom_order_client.py`
- `tests/test_approval_flow.py`

Safety rule:

- Do not turn on `ENABLE_LIVE_TRADING=true` unless the user explicitly asks and accepts real-order risk.

### MVP 5 — Limited auto-trading safety layer

Implemented:

- Scheduler-safe one-shot scan script.
- KST market scan window guard.
- Weekend skip.
- Dynamic KRX/Korea holiday calendar with API/cache/manual fallback.
- Telegram alert for pending approval ticket.
- Runtime circuit breaker state.
- Order cooldown before scheduled scans.
- Daily executed-buy amount guard.
- Scheduler/cron quiet wrapper.
- Daily realized-loss guard from `realized_pnl_events`.
- Post-fill circuit breaker automation.

Important files:

- `app/automation/scheduled_scan.py`
- `app/automation/krx_calendar.py`
- `app/automation/operational_risk.py`
- `app/automation/post_fill_risk.py`
- `scripts/run_scheduled_kiwoom_scan.py`
- `scripts/cron_kiwoom_scan.sh`
- `scripts/check_krx_holidays.py`
- `scripts/manage_runtime_risk.py`
- `scripts/record_realized_pnl_event.py`
- `tests/test_scheduled_scan.py`
- `tests/test_krx_calendar.py`
- `tests/test_operational_risk.py`
- `tests/test_post_fill_circuit_breaker.py`

Environment variables:

```bash
KIWOOM_SCAN_SYMBOL=498270
KIWOOM_SCAN_FORCE=false
KIWOOM_NOTIFY_WHEN_NO_TICKET=true
KIWOOM_ENFORCE_OPERATIONAL_RISK=true
KIWOOM_CIRCUIT_BREAKER_ENABLED=true
MAX_DAILY_BUY_AMOUNT_KRW=300000
MAX_DAILY_LOSS_KRW=50000
ORDER_COOLDOWN_MINUTES=30
KRX_HOLIDAY_SOURCE=auto
KRX_HOLIDAY_CACHE_DIR=data/calendar
KRX_HOLIDAY_YEARS=
KRX_HOLIDAY_TIMEOUT_SECONDS=10
KRX_HOLIDAYS=2026-01-01,2026-02-16,2026-02-17,2026-02-18
```

Operational flow:

```text
scheduled scan
→ market hours/weekend/holiday check
→ circuit breaker check
→ cooldown check
→ daily buy amount check
→ daily realized loss check
→ Kiwoom read workflow
→ ticket alert to Telegram
```

Post-fill safety flow:

```text
fill/position sync
→ record RealizedPnlEvent
→ sum KST same-day realized P&L
→ if <= -MAX_DAILY_LOSS_KRW
→ runtime_state.circuit_breaker = on
→ future scheduled scans blocked
```

### MVP 6 — Post-trade analysis loop

Implemented:

- Ticket/run/order event/realized P&L based post-trade analysis.
- `post_trade_analyses` persistence.
- CLI report generation.
- Deterministic outcome classification: `win`, `loss`, `flat`.
- Lessons based on risk review, order events, result, and ticket status.
- Daily Telegram post-trade digest.
- KST-date aggregation of `post_trade_analyses` with total realized P&L, `win`/`loss`/`flat` counts, ticket count, best/worst ticket, top improvement lessons, and current circuit breaker state.
- Digest CLI with `--no-send` smoke mode and optional Telegram send using existing Telegram target environment variables.

Important files:

- `app/analysis/post_trade.py`
- `app/analysis/post_trade_digest.py`
- `scripts/analyze_trade_ticket.py`
- `scripts/send_daily_post_trade_digest.py`
- `tests/test_post_trade_analysis.py`
- `tests/test_post_trade_digest.py`
- `app/storage/repository.py` (`post_trade_analyses`, `PostTradeAnalysisRecord`)

Usage:

```bash
python3 scripts/analyze_trade_ticket.py TT-...
python3 scripts/send_daily_post_trade_digest.py --date 2026-06-01 --no-send
```

Linking rule:

- `realized_pnl_events.raw_json` should include `{"ticket_id": "TT-..."}` so P&L events can be connected to tickets.

## Current DB tables of interest

- `agent_runs`
- `trade_tickets`
- `market_snapshots`
- `account_snapshots`
- `account_states`
- `risk_reviews`
- `order_events`
- `runtime_state`
- `realized_pnl_events`
- `post_trade_analyses`

## What remains to implement next

### Next immediate task: Strategy improvement memory/export loop

Goal:

- Export accumulated post-trade lessons into a durable strategy-improvement artifact.

Possible outputs:

- Markdown file under `docs/strategy-lessons.md`, or
- DB table such as `strategy_improvement_notes`, or
- Notion/Obsidian later if user asks.

Recommended behavior:

- Group lessons by symbol/date/outcome.
- Preserve source ticket IDs.
- Avoid overwriting historical notes.
- Do not store live credentials/account details.

### Later hardening

- Real fill/position sync from Kiwoom endpoints, not just manual/simulated `RealizedPnlEvent` records.
- More robust mapping from broker order/fill IDs to ticket IDs.
- Dashboard/status command for current automation health.
- CI workflow if not already present.
- Optional live order enablement checklist, only with explicit user approval.
- `live_auto` remains intentionally out of scope until safety review.

## Recommended next-session prompt

Use this in a fresh session after 5h usage quota resets:

```text
키움 REST API 거래 자동화 thread 502 이어서 진행해줘.

저장소는 /mnt/e/KiwoomAgentTrader 이고,
현재 구현 상태는 docs/implementation-handoff.md 와 docs/mvp-roadmap.md 를 먼저 읽어서 파악해줘.
현재 MVP6 post-trade analysis loop와 Daily Telegram post-trade digest까지 완료됐고,
다음 단계는 Strategy improvement memory/export loop 구현이야.

요구사항:
1. TDD로 실패 테스트 먼저 작성하고 확인
2. 누적 post_trade_analyses 개선 메모를 날짜/심볼/결과별로 집계
3. source ticket ID를 보존
4. `docs/strategy-lessons.md` 같은 durable artifact 또는 DB 테이블로 누적 export
5. 기존 일일 digest와 충돌하지 않게 읽기/내보내기 중심으로 구현
6. 전체 테스트 실행
7. Kiwoom read API smoke 확인
8. README/docs 업데이트
9. commit/push까지 완료

실주문 API는 호출하지 말고, read API와 로컬 DB/테스트만 사용해.
```

## Verification commands for next session

```bash
cd /mnt/e/KiwoomAgentTrader
git status --short --branch
python3 -m unittest discover -s tests
python3 scripts/send_daily_post_trade_digest.py --no-send
python3 scripts/check_kiwoom_read_api.py
python3 scripts/run_scheduled_kiwoom_scan.py --no-send --quiet-skip > /tmp/kiwoom_quiet.out && test ! -s /tmp/kiwoom_quiet.out && echo quiet-scheduler-ok
```

## Safety reminders

- Keep `.env` uncommitted.
- Keep account numbers masked in output.
- Do not enable `ENABLE_LIVE_TRADING=true` unless user explicitly asks.
- Do not call live order API during digest/post-trade reporting work.
- Prefer deterministic code and tests over LLM judgment for risk controls.
- Use TDD for new behavior.
