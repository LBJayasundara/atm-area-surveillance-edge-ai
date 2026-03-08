"""
Flask REST API server for the ATM Surveillance system.

Endpoints
---------
GET  /health                  — health check
GET  /alerts                  — list alerts (with optional filters)
GET  /alerts/image/<filename> — serve a snapshot image
POST /alerts/acknowledge      — acknowledge an alert
GET  /stats                   — system statistics
GET  /zones                   — list configured zones
"""

from __future__ import annotations

import os
import threading
from functools import wraps
from typing import Any, Callable, Dict, Optional

from flask import Flask, Response, jsonify, request, send_file
from flask_cors import CORS

from src.alert_manager import AlertManager
from src.logger import get_logger
from src.zones import ZoneManager

logger = get_logger(__name__)


def _build_app(
    alert_manager: AlertManager,
    zone_manager: ZoneManager,
    auth_token: Optional[str] = None,
    cors_origins: str = "*",
) -> Flask:
    """
    Create and configure the Flask application.

    Args:
        alert_manager: Shared :class:`~src.alert_manager.AlertManager` instance.
        zone_manager: Shared :class:`~src.zones.ZoneManager` instance.
        auth_token: When set, all requests must supply this token in the
                    ``X-Auth-Token`` header.
        cors_origins: Allowed CORS origin(s).

    Returns:
        Configured Flask application.
    """
    app = Flask(__name__)
    CORS(app, origins=cors_origins)

    # ------------------------------------------------------------------
    # Auth decorator
    # ------------------------------------------------------------------

    def require_auth(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if auth_token:
                supplied = request.headers.get("X-Auth-Token", "")
                if supplied != auth_token:
                    return jsonify({"error": "Unauthorised"}), 401
            return fn(*args, **kwargs)

        return wrapper

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @app.route("/health", methods=["GET"])
    def health() -> Response:
        """Return system health status."""
        return jsonify({"status": "ok", "service": "atm-surveillance"})

    @app.route("/alerts", methods=["GET"])
    @require_auth
    def list_alerts() -> Response:
        """
        List alerts with optional filtering and pagination.

        Query parameters:
            limit (int, default 50)
            offset (int, default 0)
            activity_type (str, optional)
            acknowledged (bool, optional)
        """
        try:
            limit = min(int(request.args.get("limit", 50)), 200)
            offset = int(request.args.get("offset", 0))
        except ValueError:
            return jsonify({"error": "Invalid pagination parameters"}), 400

        activity_type = request.args.get("activity_type")
        ack_str = request.args.get("acknowledged")
        acknowledged: Optional[bool] = None
        if ack_str is not None:
            acknowledged = ack_str.lower() in ("true", "1", "yes")

        alerts = alert_manager.get_alerts(
            limit=limit,
            offset=offset,
            activity_type=activity_type,
            acknowledged=acknowledged,
        )
        return jsonify({"alerts": alerts, "count": len(alerts)})

    @app.route("/alerts/image/<filename>", methods=["GET"])
    @require_auth
    def serve_image(filename: str) -> Response:
        """Serve a snapshot image by filename."""
        path = alert_manager.snapshot_path(filename)
        if path is None:
            return jsonify({"error": "Image not found"}), 404
        return send_file(path, mimetype="image/jpeg")

    @app.route("/alerts/acknowledge", methods=["POST"])
    @require_auth
    def acknowledge_alert() -> Response:
        """
        Acknowledge an alert.

        Request body (JSON):
            {"alert_id": "<id>"}
        """
        data = request.get_json(silent=True) or {}
        alert_id = data.get("alert_id", "").strip()
        if not alert_id:
            return jsonify({"error": "alert_id is required"}), 400

        success = alert_manager.acknowledge_alert(alert_id)
        if not success:
            return jsonify({"error": "Alert not found"}), 404
        return jsonify({"message": f"Alert {alert_id} acknowledged."})

    @app.route("/stats", methods=["GET"])
    @require_auth
    def get_stats() -> Response:
        """Return alert statistics."""
        return jsonify(alert_manager.get_stats())

    @app.route("/zones", methods=["GET"])
    @require_auth
    def list_zones() -> Response:
        """Return all configured zones."""
        zones = [
            {
                "name": z.name,
                "zone_type": z.zone_type,
                "description": z.description,
                "polygon": z.polygon,
            }
            for z in zone_manager.zones.values()
        ]
        return jsonify({"zones": zones})

    return app


class APIServer:
    """
    Wraps the Flask app and runs it in a background thread.
    """

    def __init__(
        self,
        alert_manager: AlertManager,
        zone_manager: ZoneManager,
        host: str = "0.0.0.0",
        port: int = 5000,
        auth_token: Optional[str] = None,
        debug: bool = False,
    ) -> None:
        """
        Initialise the API server.

        Args:
            alert_manager: Shared alert manager instance.
            zone_manager: Shared zone manager instance.
            host: Bind host address.
            port: Bind port number.
            auth_token: Optional shared secret for request authentication.
            debug: Enable Flask debug mode (development only).
        """
        self.host = host
        self.port = port
        self.debug = debug

        self._app = _build_app(alert_manager, zone_manager, auth_token)
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the Flask server in a background daemon thread."""
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="api-server"
        )
        self._thread.start()
        logger.info("API server started at http://%s:%d", self.host, self.port)

    def _run(self) -> None:
        """Internal: run Flask (blocks until process exits)."""
        import logging as _logging
        # Suppress Flask's startup messages in production
        _logging.getLogger("werkzeug").setLevel(_logging.WARNING)
        self._app.run(host=self.host, port=self.port, debug=self.debug, use_reloader=False)
