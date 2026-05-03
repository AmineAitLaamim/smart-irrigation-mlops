from src.drift_detector import kl_divergence, page_hinkley, summarize_drift


def test_page_hinkley_detects_shift():
    score, detected = page_hinkley([0.1, 0.1, 0.1, 1.0, 1.0], threshold=0.1)
    assert score >= 0
    assert detected is True


def test_kl_divergence_non_negative():
    divergence = kl_divergence([0.1, 0.2, 0.3], [0.3, 0.4, 0.5])
    assert divergence >= 0


def test_summarize_drift_sets_flag():
    summary = summarize_drift([0.1, 0.2, 0.2], [0.8, 0.9, 1.0])
    assert summary.drift_detected is True
