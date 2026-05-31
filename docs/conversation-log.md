# Telegram Thread 502 Conversation Log — Kiwoom Agent Trader

**Date:** 2026-05-31  
**Source:** Telegram group `hermes`, thread `502`  
**Topic:** 키움증권 REST API 기반 거래 자동화 / 멀티 에이전트 투자 시스템

## Conversation Summary

이 방은 키움증권 REST API를 이용한 거래 자동화 구축 대화를 위한 공간으로 정의되었다. 초기 제안은 Python 스크립트 기반 자동매매 구조였으나, 사용자는 단순 스크립트 자동화보다 **에이전트 기반 자동화**, 특히 **멀티 에이전트 구조**를 선호한다고 밝혔다.

확정된 방향은 다음과 같다.

> 키움증권 REST API를 도구로 사용하는 멀티 에이전트 기반 투자 의사결정 및 거래 실행 시스템.

## Key User Requirements

1. 프로젝트는 Python 스크립트 중심 자동화가 아니라 **에이전트 기반 자동화**로 구축한다.
2. 멀티 에이전트 구성에는 시장 분석, 종목 추천, 매매 전략, 리스크 관리, 거래 실행 에이전트가 포함된다.
3. 먼저 설계 문서를 작성한 뒤, 프로젝트 스캐폴딩을 진행한다.
4. 프로젝트 폴더는 `E:/` 하위에 생성한다.
5. GitHub 레포지토리 `https://github.com/KevinFire2030/KiwoomAgentTrader.git`에 연결하고 푸시한다.
6. 이 방의 대화 내용을 기록으로 저장하고 GitHub에 푸시한다.
7. LLM Wiki에도 정리하여 지식화한다.

## Initial Assistant Proposal

초기에는 전통적인 자동매매 봇 구조가 제안되었다.

```text
Scheduler → Market Data Collector → Strategy Engine → Risk Guard → Order Manager → PaperBroker or LiveBroker → Kiwoom REST API → Storage + Telegram Notify
```

주요 모듈은 `kiwoom/`, `strategy/`, `risk/`, `execution/`, `storage/`, `notify/`였다.

## User Correction: Agent-Based Concept

사용자는 다음과 같이 방향을 수정했다.

> 컨셉을 파이썬 스크립트 기반 자동화보다 에이전트 기반 자동화로 구축하고 싶어.

예시 구성:

- 시장 분석 에이전트
- 종목 추천 에이전트
- 매매 전략 에이전트
- 리스크관리 에이전트
- 실제로 매매를 담당하는 에이전트

## Agreed Concept

# Kiwoom Agent Trader

키움증권 REST API를 사용하는 **멀티 에이전트 기반 투자 의사결정 및 거래 실행 시스템**.

핵심 철학:

1. 에이전트는 역할별로 분리한다.
2. 주문 권한은 거래 실행 에이전트에게만 준다.
3. 리스크 관리 에이전트가 반드시 승인해야 한다.
4. 실거래는 초기에 사람 승인을 요구한다.
5. 모든 판단과 주문은 DB에 저장한다.
6. LLM은 판단과 설명을 담당하고, 주문 검증은 deterministic code가 담당한다.

## Confirmed MVP

1차 MVP:

> `498270 KIWOOM 미국양자컴퓨팅 ETF`에 대해 멀티 에이전트가 분석 회의를 수행하고, 주문 후보 티켓을 만들고, 텔레그램으로 승인 요청을 보내는 PoC.

초기 모드는 `paper`이며 실제 주문은 하지 않는다.

<!-- AUTO_SYNC_STATUS_START -->
## Auto Sync Status

이 파일 외에 전체 원문 대화 로그는 `docs/telegram-thread-502-full-log.md`에 자동 저장됩니다.

- Latest message ID: 1867
- Latest message time: 2026-05-31 10:10:51 UTC+09:00
- Synced sessions: 2
- Synced messages: 32
- Sync method: Hermes cron job `Kiwoom thread 502 auto GitHub sync`
<!-- AUTO_SYNC_STATUS_END -->







