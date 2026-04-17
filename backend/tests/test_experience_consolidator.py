from xoai.agents.experience_consolidator import _aggregate_utility_components, _build_comparative_summary


def test_aggregate_utility_components_averages_values():
    lessons = [
        {
            "utility_components": {
                "success_delta": 0.9,
                "reuse_rate": 0.6,
                "severity": 0.2,
                "freshness": 1.0,
                "confidence": 0.8,
            }
        },
        {
            "utility_components": {
                "success_delta": 0.5,
                "reuse_rate": 0.4,
                "severity": 0.6,
                "freshness": 0.8,
                "confidence": 0.7,
            }
        },
    ]
    aggregated = _aggregate_utility_components(lessons)
    assert aggregated["success_delta"] == 0.7
    assert aggregated["reuse_rate"] == 0.5
    assert aggregated["confidence"] == 0.75
    assert 0.0 <= aggregated["utility_score"] <= 1.0


def test_build_comparative_summary_reports_utility_gap():
    success_lessons = [{"utility_score": 0.8}, {"utility_score": 0.6}]
    failure_lessons = [{"utility_score": 0.4}]
    summary = _build_comparative_summary(success_lessons, failure_lessons)
    assert summary["success_count"] == 2
    assert summary["failure_count"] == 1
    assert summary["utility_gap"] > 0
