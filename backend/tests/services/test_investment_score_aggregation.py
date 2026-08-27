from app.models.investment_score_aggregation import (
    WeightedScoreAggregation,
)
from app.services.investment_score_aggregation import (
    InvestmentScoreAggregationService,
)


def test_restomart_weighted_score(
    scorecard,
    multi_dimension_evaluation,
):
    result = (
        InvestmentScoreAggregationService.calculate(
            scorecard=scorecard,
            evaluation=multi_dimension_evaluation,
        )
    )

    assert result.total_weight == 100

    assert result.overall_score == 74.75

def test_weighted_contributions(
    scorecard,
    multi_dimension_evaluation,
):
    result = (
        InvestmentScoreAggregationService.calculate(
            scorecard=scorecard,
            evaluation=multi_dimension_evaluation,
        )
    )

    contributions = {
        item.dimension_id: item.weighted_score
        for item in result.dimension_scores
    }

    assert contributions["founder_team"] == 12.75
    assert contributions["market_tam"] == 6.0
    assert contributions["commercial_traction"] == 12.75
    assert contributions["valuation_deal_terms"] == 7.0
