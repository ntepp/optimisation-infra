from src.domain.forecasting import (
    LinearForecaster, PatternDetector, RiskClassifier,
)


# ── LinearForecaster ─────────────────────────────────────────────────────────

def test_linear_forecaster_empty_input_returns_none():
    assert LinearForecaster().forecast("cpu", []) is None


def test_linear_forecaster_single_value_returns_stable_pattern():
    f = LinearForecaster().forecast("disk_usage", [50.0])
    assert f is not None
    assert f.trend == "stable"
    assert f.predicted_value == 50.0


def test_linear_forecaster_detects_rising_trend():
    f = LinearForecaster().forecast("disk_usage", [10.0, 20.0, 30.0, 40.0, 50.0])
    assert f is not None
    assert f.trend == "increasing"
    assert f.predicted_value > 50.0


def test_linear_forecaster_detects_decreasing_trend():
    f = LinearForecaster().forecast("memory_usage", [80.0, 70.0, 60.0, 50.0, 40.0])
    assert f is not None
    assert f.trend == "decreasing"
    assert f.predicted_value < 40.0


def test_linear_forecaster_classifies_small_slope_as_stable():
    f = LinearForecaster().forecast("memory_usage", [50.0, 50.1, 50.0, 50.2, 50.1])
    assert f is not None
    assert f.trend == "stable"


# ── PatternDetector ─────────────────────────────────────────────────────────

def test_pattern_detector_precursor_for_three_consecutive_rises():
    f = PatternDetector().detect("cpu_usage", [40.0, 50.0, 60.0, 70.0, 85.0])
    assert f is not None
    assert f.pattern == "PRECURSOR"
    assert f.trend == "increasing"
    assert f.predicted_value > 85.0


def test_pattern_detector_rising_for_last_two_increasing():
    f = PatternDetector().detect("cpu_usage", [90.0, 50.0, 60.0])
    assert f is not None
    assert f.pattern == "RISING"
    assert f.trend == "increasing"


def test_pattern_detector_declining_for_last_two_decreasing():
    f = PatternDetector().detect("cpu_usage", [50.0, 90.0, 60.0])
    assert f is not None
    assert f.pattern == "DECLINING"
    assert f.trend == "decreasing"


def test_pattern_detector_stable_fallback_for_flat_history():
    f = PatternDetector().detect("cpu_usage", [50.0, 50.0, 50.0])
    assert f is not None
    assert f.pattern == "STABLE"
    assert f.trend == "stable"


def test_pattern_detector_insufficient_data_for_single_value():
    f = PatternDetector().detect("cpu_usage", [50.0])
    assert f is not None
    assert f.pattern == "INSUFFICIENT_DATA"


# ── RiskClassifier ──────────────────────────────────────────────────────────

def test_risk_classifier_normal_below_warning():
    rc = RiskClassifier({"cpu_usage": {"warning": 80.0, "critical": 90.0}})
    assert rc.classify("cpu_usage", 50.0) == "NORMAL"


def test_risk_classifier_warning_above_warning_below_critical():
    rc = RiskClassifier({"cpu_usage": {"warning": 80.0, "critical": 90.0}})
    assert rc.classify("cpu_usage", 85.0) == "WARNING"


def test_risk_classifier_critical_above_critical():
    rc = RiskClassifier({"cpu_usage": {"warning": 80.0, "critical": 90.0}})
    assert rc.classify("cpu_usage", 95.0) == "CRITICAL"


def test_risk_classifier_unknown_metric_returns_normal():
    rc = RiskClassifier({})
    assert rc.classify("unknown_metric", 1000.0) == "NORMAL"
