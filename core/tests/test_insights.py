"""Theme performance alerts: latest-week vs rolling-baseline anomaly detection."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from invisable_os.engines import detect_theme_alerts
from invisable_os.main import app
from invisable_os.services import theme_alerts

client = TestClient(app)

NOW = datetime(2026, 6, 24, tzinfo=UTC)


def _sig(theme, metric, value, when):
    return {"metric": metric, "value": value, "themes": [theme], "observed_at": when.isoformat()}


def _dataset():
    """Humour saves collapse −40%, education saves climb +60%, vs a 4-week baseline."""
    base = [datetime(2026, 5, 25, tzinfo=UTC), datetime(2026, 6, 1, tzinfo=UTC),
            datetime(2026, 6, 8, tzinfo=UTC)]
    cur = [datetime(2026, 6, 20, tzinfo=UTC), datetime(2026, 6, 22, tzinfo=UTC)]
    signals = []
    for w in base:
        signals += [_sig("humour", "saves", 100, w), _sig("education", "saves", 50, w)]
    for w in cur:
        signals += [_sig("humour", "saves", 60, w), _sig("education", "saves", 80, w)]
    return signals


# --- pure detection ---------------------------------------------------------


def test_detects_decline_and_momentum():
    alerts = detect_theme_alerts(_dataset(), now=NOW)
    by_theme = {a["theme"]: a for a in alerts}
    assert by_theme["humour"]["direction"] == "down"
    assert by_theme["humour"]["change_pct"] == -40.0
    assert by_theme["education"]["direction"] == "up"
    assert by_theme["education"]["change_pct"] == 60.0
    # Biggest mover ranks first.
    assert alerts[0]["theme"] == "education"
    assert "rebalance" in by_theme["humour"]["recommendation"]


def test_below_threshold_is_not_flagged():
    base = datetime(2026, 6, 1, tzinfo=UTC)
    cur = datetime(2026, 6, 21, tzinfo=UTC)
    signals = [
        _sig("steady", "saves", 100, base), _sig("steady", "saves", 100, base),
        _sig("steady", "saves", 105, cur), _sig("steady", "saves", 105, cur),  # +5%
    ]
    assert detect_theme_alerts(signals, now=NOW) == []


def test_ignores_non_alert_metrics():
    base = datetime(2026, 6, 1, tzinfo=UTC)
    cur = datetime(2026, 6, 21, tzinfo=UTC)
    signals = [
        _sig("x", "follower_growth", 100, base), _sig("x", "follower_growth", 100, base),
        _sig("x", "follower_growth", 10, cur), _sig("x", "follower_growth", 10, cur),
    ]
    assert detect_theme_alerts(signals, now=NOW) == []


def test_needs_baseline_and_current_samples():
    # Only current-window data, no baseline → nothing to compare against.
    cur = datetime(2026, 6, 21, tzinfo=UTC)
    signals = [_sig("y", "saves", 100, cur), _sig("y", "saves", 100, cur)]
    assert detect_theme_alerts(signals, now=NOW) == []


# --- service ----------------------------------------------------------------


class _FakeRepo:
    def __init__(self, signals):
        self._signals = signals

    def list_signals(self):
        return self._signals


def test_theme_alerts_service():
    out = theme_alerts(repository=_FakeRepo(_dataset()), now=NOW)
    assert out["count"] == 2
    assert out["momentum"] == 1
    assert out["declining"] == 1


def test_theme_alerts_service_empty():
    out = theme_alerts(repository=_FakeRepo([]), now=NOW)
    assert out == {"count": 0, "momentum": 0, "declining": 0, "alerts": []}


# --- endpoint ---------------------------------------------------------------


def test_brain_alerts_endpoint():
    r = client.get("/v1/brain/alerts")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"count", "momentum", "declining", "alerts"}
