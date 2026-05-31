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

저장되는 데이터:

- `market_snapshots`: 현재가, 등락률, 원본 응답 JSON
- `account_snapshots`: 마스킹 계좌번호, 예수금/추정자산, 평가금액, 보유종목 수
- `account_states`: Account State Agent가 계산한 현금흐름/투자 가능 현금
- `agent_runs`, `trade_tickets`, `risk_reviews`: 에이전트 판단/리스크 심사 이력
