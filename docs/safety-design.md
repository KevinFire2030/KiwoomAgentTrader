# Kiwoom Agent Trader Safety Design

## Goal

멀티 에이전트 구조에서 LLM 판단이 직접 실거래 주문으로 이어지지 않도록 권한, 승인, 정책, 검증 계층을 분리한다.

## Safety Principles

1. 실거래는 기본 OFF.
2. 주문 API 권한은 Trade Execution Agent에만 있다.
3. Risk Management Agent 승인 없는 주문은 불가능하다.
4. live_manual 모드에서는 사용자 승인 없는 주문은 불가능하다.
5. LLM이 산출한 주문 제안은 deterministic policy code가 다시 검증한다.
6. 모든 판단과 주문은 감사 가능한 로그로 남긴다.
7. 에이전트는 자신에게 허용된 도구만 사용할 수 있다.

## Trading Modes

- `advisory`: 분석 리포트만 생성한다.
- `paper`: Trade Ticket과 paper order를 생성한다. 키움 주문 API는 호출하지 않는다.
- `live_manual`: Risk 승인 + 사용자 승인 후 `live_manual_ready` 상태까지 준비한다. 실제 키움 주문 제출은 `ENABLE_LIVE_TRADING=true`가 별도로 켜져야 한다.
- `live_auto`: 제한된 종목/금액/시간 조건 안에서만 자동 주문한다. MVP 범위에서 제외한다.

## Risk Policy Defaults

- allowed symbol: `498270`
- max order amount: 100,000 KRW
- max daily buy amount: 300,000 KRW
- max daily loss: 50,000 KRW, calculated from KST same-day `realized_pnl_events`
- order cooldown: 30 minutes
- live trading: disabled
- auto order: disabled

## Trade Ticket Guardrails

Trade Execution Agent는 티켓 존재, risk approval, 만료 전, 허용 종목, 정책 한도, 승인 수량 이하, 실행 모드 허용 조건을 모두 만족해야 실행할 수 있다.

## Failure Handling

Kiwoom API 인증 실패, 계좌/포지션 검증 실패, 정책 로드 실패, 중복 티켓/주문 감지, 일일 손실 한도 도달, 주문 전 로그 저장 실패 시 모든 신규 주문을 차단한다. 체결/포지션 동기화에서 당일 실현손실 한도 초과가 감지되면 post-fill circuit breaker가 `runtime_state.circuit_breaker=on`으로 전환해 후속 정기 스캔을 차단한다.

## Audit Trail

Every workflow run must save run_id, agent inputs/outputs, risk decision, ticket state changes, order request/response, and user approval message if applicable. `order_events` records final approval blocks, live submissions, broker rejections, request payloads, broker responses, and status messages for each ticket.
