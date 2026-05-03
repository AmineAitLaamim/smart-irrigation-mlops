from mlops.evaluation import compare_prediction_streams, summarize_evaluation


def test_compare_prediction_streams_returns_shadow_metrics():
    result = compare_prediction_streams(
        actual=[10.0, 12.0, 11.0],
        candidate=[10.5, 11.5, 10.5],
        production=[11.0, 13.0, 12.0],
    )
    assert "paired_t_like_score" in result
    assert "diebold_mariano_like_score" in result


def test_summarize_evaluation_marks_better_candidate():
    summary = summarize_evaluation(
        actual=[10.0, 12.0, 11.0],
        candidate_predictions=[10.1, 11.9, 11.1],
        production_predictions=[11.0, 13.0, 12.0],
    )
    assert summary.promoted is True
    assert summary.confidence_interval_high >= summary.confidence_interval_low
