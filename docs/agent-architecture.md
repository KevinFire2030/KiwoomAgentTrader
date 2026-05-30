# Kiwoom Agent Trader Agent Architecture

## Goal

키움증권 REST API를 도구로 사용하는 멀티 에이전트 기반 투자 의사결정 및 거래 실행 시스템을 설계한다.

## Architecture Principle

LLM Agent는 분석, 판단, 설명, 제안을 담당한다. 실제 숫자 계산, 주문 한도 검증, 승인 상태 검증, 키움 주문 API 호출은 deterministic code가 담당한다.

```text
User / Scheduler → Chief Investment Agent → Market Analysis Agent → Stock Recommendation Agent → Trading Strategy Agent → Risk Management Agent → Trade Execution Agent → Kiwoom REST API / Paper Broker → Post Trade Analysis Agent
```

## Agents

### Chief Investment Agent

전체 워크플로우 시작/종료, run_id 생성, 하위 에이전트 호출 순서 관리, 결과 취합, 최종 리포트 생성, 사용자 승인 요청을 담당한다. 직접 주문 실행은 금지된다.

### Market Analysis Agent

시장 레짐(`risk_on`, `neutral`, `risk_off`) 판단, 시장 요약, 위험 요인 식별을 담당한다. 주문 권한은 없다.

### Stock Recommendation Agent

관심종목 점수화, watch/buy_candidate/avoid 판단, 추천 근거 설명을 담당한다. 초기 universe는 `498270` KIWOOM 미국양자컴퓨팅 ETF이다.

### Trading Strategy Agent

매수/매도/관망 판단, 분할 매수/매도 계획, Trade Ticket 후보 생성을 담당한다. 실제 주문 API 호출은 금지된다.

### Risk Management Agent

Trade Ticket 심사, 주문 수량/금액 축소, 주문 거부, 리스크 사유 기록을 담당한다. 전략 제안보다 주문을 늘릴 수 없다.

### Trade Execution Agent

승인된 Trade Ticket만 실행한다. paper/live 실행 모드를 분기하고 주문 결과를 저장한다.

### Post Trade Analysis Agent

주문/체결 결과 복기, 전략 품질 평가, 다음 액션 제안을 담당한다.

## Trade Ticket

```json
{
  "ticket_id": "TT-20260531-0001",
  "symbol": "498270",
  "side": "buy",
  "quantity": 3,
  "order_type": "limit",
  "limit_price": 12340,
  "created_by": "trading_strategy_agent",
  "risk_approved": true,
  "risk_approved_by": "risk_management_agent",
  "user_approved": false,
  "status": "pending_user_approval",
  "expires_at": "2026-05-31T10:00:00+09:00"
}
```

## Workflow: MVP Paper Mode

1. Chief Agent creates `run_id`.
2. Market Analysis Agent produces market regime.
3. Stock Recommendation Agent scores `498270`.
4. Trading Strategy Agent creates a Trade Ticket candidate.
5. Risk Management Agent approves, adjusts, or rejects the ticket.
6. Chief Agent produces final Telegram-ready report.
7. Trade Execution Agent records a paper order only if approved.
8. TradingRepository persists the agent run, Trade Ticket, and risk review to SQLite.

## Storage Requirements

`agent_runs`, `agent_messages`, `recommendations`, `strategy_decisions`, `trade_tickets`, `risk_reviews`, `orders`, `executions`, `post_trade_reviews`.
