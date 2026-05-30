from app.agents.models import Recommendation


class StockRecommendationAgent:
    name = "stock_recommendation_agent"

    def recommend(self, symbol: str) -> Recommendation:
        if symbol != "498270":
            return Recommendation(self.name, symbol, "unknown", "avoid", 0, "MVP 허용 종목이 아닙니다.")
        return Recommendation(
            agent=self.name,
            symbol="498270",
            name="KIWOOM 미국양자컴퓨팅 ETF",
            action_bias="watch",
            score=60,
            reason="MVP 관심종목으로 추적하되, 실제 시세/뉴스 연동 전이므로 관찰 의견을 유지합니다.",
        )
