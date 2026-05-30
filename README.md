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
