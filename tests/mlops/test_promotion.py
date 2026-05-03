from mlops.promotion import decide_promotion


def test_decide_promotion_allows_first_model():
    decision = decide_promotion(candidate_rmse=0.8, production_rmse=None)
    assert decision.should_promote is True
    assert decision.target_stage == "Production"


def test_decide_promotion_requires_margin():
    decision = decide_promotion(candidate_rmse=0.95, production_rmse=0.96, min_improvement=0.02)
    assert decision.should_promote is False
    assert decision.target_stage == "Staging"
