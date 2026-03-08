"""Unit tests for the Flask REST API (src/api_server.py)."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from src.alert_manager import AlertManager
from src.api_server import _build_app
from src.zones import Zone, ZoneManager


@pytest.fixture()
def app():
    """Create a test Flask application with a temp database."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test_alerts.db")
        snapshot_dir = os.path.join(tmp, "snapshots")
        am = AlertManager(db_path=db_path, snapshot_dir=snapshot_dir)
        zone = Zone(name="test_zone", polygon=[(0, 0), (100, 0), (100, 100), (0, 100)])
        zm = ZoneManager([zone])
        flask_app = _build_app(am, zm, auth_token="test-token")
        flask_app.config["TESTING"] = True
        yield flask_app, am


@pytest.fixture()
def client(app):
    flask_app, am = app
    return flask_app.test_client(), am


class TestHealthEndpoint:
    def test_health_no_auth_required(self, client):
        c, _ = client
        resp = c.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"


class TestAlertsEndpoint:
    def test_list_alerts_requires_auth(self, client):
        c, _ = client
        resp = c.get("/alerts")
        assert resp.status_code == 401

    def test_list_alerts_with_auth_empty(self, client):
        c, _ = client
        resp = c.get("/alerts", headers={"X-Auth-Token": "test-token"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["alerts"] == []
        assert data["count"] == 0

    def test_list_alerts_invalid_pagination(self, client):
        c, _ = client
        resp = c.get(
            "/alerts?limit=bad", headers={"X-Auth-Token": "test-token"}
        )
        assert resp.status_code == 400

    def test_acknowledge_missing_alert_id(self, client):
        c, _ = client
        resp = c.post(
            "/alerts/acknowledge",
            json={},
            headers={"X-Auth-Token": "test-token"},
        )
        assert resp.status_code == 400

    def test_acknowledge_nonexistent_alert(self, client):
        c, _ = client
        resp = c.post(
            "/alerts/acknowledge",
            json={"alert_id": "nonexistent_id"},
            headers={"X-Auth-Token": "test-token"},
        )
        assert resp.status_code == 404


class TestStatsEndpoint:
    def test_stats_returns_dict(self, client):
        c, _ = client
        resp = c.get("/stats", headers={"X-Auth-Token": "test-token"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "total_alerts" in data
        assert data["total_alerts"] == 0


class TestZonesEndpoint:
    def test_list_zones(self, client):
        c, _ = client
        resp = c.get("/zones", headers={"X-Auth-Token": "test-token"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["zones"]) == 1
        assert data["zones"][0]["name"] == "test_zone"


class TestImageEndpoint:
    def test_image_not_found(self, client):
        c, _ = client
        resp = c.get(
            "/alerts/image/no_such_file.jpg",
            headers={"X-Auth-Token": "test-token"},
        )
        assert resp.status_code == 404

    def test_path_traversal_rejected(self, client):
        """Verify that path-traversal filenames return 404 rather than serving files."""
        c, _ = client
        resp = c.get(
            "/alerts/image/../../etc/passwd",
            headers={"X-Auth-Token": "test-token"},
        )
        # Flask treats this URL as not-found at routing level or returns 404
        assert resp.status_code in (404, 400)
