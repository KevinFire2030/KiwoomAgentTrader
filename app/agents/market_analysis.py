from app.agents.models import MarketAnalysis


class MarketAnalysisAgent:
    name = "market_analysis_agent"

    def analyze(self) -> MarketAnalysis:
        return MarketAnalysis(
            agent=self.name,
            market_regime="neutral",
            confidence=0.55,
            summary="MVP 초기 버전에서는 외부 시장 데이터 연동 전이므로 중립 레짐으로 판단합니다.",
            warnings=["실시간 시장 데이터 연동 전까지 보수적 판단 필요"],
        )
