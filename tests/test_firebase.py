"""
Unit tests for src/firebase_client.py.

All Firebase Admin SDK calls are mocked so these tests run without real
Firebase credentials or network access.
"""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers — build a minimal firebase_admin stub so the module can be imported
# without the real package installed.
# ---------------------------------------------------------------------------


def _make_firebase_stub() -> ModuleType:
    """Return a minimal mock of the firebase_admin package hierarchy."""
    fb = ModuleType("firebase_admin")
    fb._apps = {}  # type: ignore[attr-defined]
    fb.initialize_app = MagicMock()

    # credentials sub-module
    creds_mod = ModuleType("firebase_admin.credentials")
    creds_mod.Certificate = MagicMock(return_value=MagicMock())
    fb.credentials = creds_mod  # type: ignore[attr-defined]

    # firestore sub-module
    fs_mod = ModuleType("firebase_admin.firestore")
    fs_mod.SERVER_TIMESTAMP = "SERVER_TIMESTAMP_SENTINEL"
    fs_mod.Query = MagicMock()
    fs_mod.Query.DESCENDING = "DESCENDING"

    mock_doc_ref = MagicMock()
    mock_doc_ref.set = MagicMock()
    mock_doc_ref.update = MagicMock()

    mock_collection = MagicMock()
    mock_collection.document = MagicMock(return_value=mock_doc_ref)
    mock_collection.order_by = MagicMock(return_value=mock_collection)
    mock_collection.where = MagicMock(return_value=mock_collection)
    mock_collection.limit = MagicMock(return_value=mock_collection)
    mock_collection.stream = MagicMock(return_value=[])

    mock_db = MagicMock()
    mock_db.collection = MagicMock(return_value=mock_collection)

    fs_mod.client = MagicMock(return_value=mock_db)
    fb.firestore = fs_mod  # type: ignore[attr-defined]

    # storage sub-module
    st_mod = ModuleType("firebase_admin.storage")
    mock_bucket = MagicMock()
    st_mod.bucket = MagicMock(return_value=mock_bucket)
    fb.storage = st_mod  # type: ignore[attr-defined]

    # messaging sub-module
    msg_mod = ModuleType("firebase_admin.messaging")
    msg_mod.Message = MagicMock()
    msg_mod.Notification = MagicMock()
    msg_mod.send = MagicMock(return_value="message-id-stub")
    fb.messaging = msg_mod  # type: ignore[attr-defined]

    return fb


@pytest.fixture(autouse=True)
def mock_firebase_admin(tmp_path):
    """
    Patch sys.modules with a firebase_admin stub and reload FirebaseClient
    so every test gets a clean module state.
    """
    stub = _make_firebase_stub()
    modules_to_patch = {
        "firebase_admin": stub,
        "firebase_admin.credentials": stub.credentials,  # type: ignore[attr-defined]
        "firebase_admin.firestore": stub.firestore,  # type: ignore[attr-defined]
        "firebase_admin.storage": stub.storage,  # type: ignore[attr-defined]
        "firebase_admin.messaging": stub.messaging,  # type: ignore[attr-defined]
    }

    # Create a dummy credentials file
    cred_file = tmp_path / "firebase-credentials.json"
    cred_file.write_text('{"type": "service_account"}')

    with patch.dict(sys.modules, modules_to_patch):
        # Force re-import so module-level availability check uses the stub
        if "src.firebase_client" in sys.modules:
            del sys.modules["src.firebase_client"]
        yield stub, str(cred_file)

    # Clean up after each test
    if "src.firebase_client" in sys.modules:
        del sys.modules["src.firebase_client"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFirebaseClientInit:
    def test_available_with_valid_credentials(self, mock_firebase_admin):
        stub, cred_path = mock_firebase_admin
        stub._apps = {}  # type: ignore[attr-defined]

        from src.firebase_client import FirebaseClient

        client = FirebaseClient(
            credentials_path=cred_path,
            storage_bucket="test.appspot.com",
        )
        assert client.available is True

    def test_unavailable_when_credentials_file_missing(self, mock_firebase_admin):
        _stub, _cred_path = mock_firebase_admin
        from src.firebase_client import FirebaseClient

        client = FirebaseClient(
            credentials_path="/nonexistent/firebase.json",
            storage_bucket="test.appspot.com",
        )
        assert client.available is False

    def test_default_collection_and_topic(self, mock_firebase_admin):
        stub, cred_path = mock_firebase_admin
        stub._apps = {}  # type: ignore[attr-defined]
        from src.firebase_client import FirebaseClient

        client = FirebaseClient(
            credentials_path=cred_path,
            storage_bucket="test.appspot.com",
        )
        assert client._collection_name == "alerts"
        assert client._fcm_topic == "atm_alerts"

    def test_custom_collection_and_topic(self, mock_firebase_admin):
        stub, cred_path = mock_firebase_admin
        stub._apps = {}  # type: ignore[attr-defined]
        from src.firebase_client import FirebaseClient

        client = FirebaseClient(
            credentials_path=cred_path,
            storage_bucket="test.appspot.com",
            collection_name="custom_alerts",
            fcm_topic="custom_topic",
        )
        assert client._collection_name == "custom_alerts"
        assert client._fcm_topic == "custom_topic"


class TestFirebaseClientCreateAlert:
    def _make_client(self, cred_path, stub):
        stub._apps = {}  # type: ignore[attr-defined]
        from src.firebase_client import FirebaseClient

        return FirebaseClient(
            credentials_path=cred_path,
            storage_bucket="test.appspot.com",
        )

    def test_create_alert_returns_alert_id(self, mock_firebase_admin):
        stub, cred_path = mock_firebase_admin
        client = self._make_client(cred_path, stub)

        alert_data = {
            "id": "alert_test_001",
            "activity": "Weapon Detected",
            "activity_type": "weapon",
            "detected_object": "gun",
            "confidence": 0.91,
            "location": "ATM Entrance",
        }
        result = client.create_alert(alert_data)
        assert result == "alert_test_001"

    def test_create_alert_uses_provided_id(self, mock_firebase_admin):
        stub, cred_path = mock_firebase_admin
        client = self._make_client(cred_path, stub)

        alert_data = {"id": "my_custom_id", "activity_type": "loitering"}
        result = client.create_alert(alert_data)
        assert result == "my_custom_id"

    def test_create_alert_generates_id_when_missing(self, mock_firebase_admin):
        stub, cred_path = mock_firebase_admin
        client = self._make_client(cred_path, stub)

        result = client.create_alert({"activity_type": "concealment"})
        assert result is not None
        assert result.startswith("alert_")

    def test_create_alert_returns_none_when_unavailable(self, mock_firebase_admin):
        stub, cred_path = mock_firebase_admin
        from src.firebase_client import FirebaseClient

        client = FirebaseClient(
            credentials_path="/nonexistent/creds.json",
            storage_bucket="test.appspot.com",
        )
        result = client.create_alert({"activity_type": "weapon"})
        assert result is None


class TestFirebaseClientUpdateAlert:
    def test_update_alert_returns_true_when_available(self, mock_firebase_admin):
        stub, cred_path = mock_firebase_admin
        stub._apps = {}  # type: ignore[attr-defined]
        from src.firebase_client import FirebaseClient

        client = FirebaseClient(
            credentials_path=cred_path,
            storage_bucket="test.appspot.com",
        )
        result = client.update_alert("alert_001", {"acknowledged": True})
        assert result is True

    def test_update_alert_returns_false_when_unavailable(self, mock_firebase_admin):
        _stub, _cred_path = mock_firebase_admin
        from src.firebase_client import FirebaseClient

        client = FirebaseClient(
            credentials_path="/nonexistent/creds.json",
            storage_bucket="test.appspot.com",
        )
        result = client.update_alert("alert_001", {"acknowledged": True})
        assert result is False


class TestFirebaseClientAcknowledgeAlert:
    def test_acknowledge_alert_calls_update(self, mock_firebase_admin):
        stub, cred_path = mock_firebase_admin
        stub._apps = {}  # type: ignore[attr-defined]
        from src.firebase_client import FirebaseClient

        client = FirebaseClient(
            credentials_path=cred_path,
            storage_bucket="test.appspot.com",
        )
        result = client.acknowledge_alert("alert_001")
        assert result is True


class TestFirebaseClientGetAlerts:
    def test_get_alerts_returns_list_when_available(self, mock_firebase_admin):
        stub, cred_path = mock_firebase_admin
        stub._apps = {}  # type: ignore[attr-defined]
        from src.firebase_client import FirebaseClient

        client = FirebaseClient(
            credentials_path=cred_path,
            storage_bucket="test.appspot.com",
        )
        result = client.get_alerts()
        assert isinstance(result, list)

    def test_get_alerts_returns_empty_list_when_unavailable(self, mock_firebase_admin):
        _stub, _cred_path = mock_firebase_admin
        from src.firebase_client import FirebaseClient

        client = FirebaseClient(
            credentials_path="/nonexistent/creds.json",
            storage_bucket="test.appspot.com",
        )
        result = client.get_alerts()
        assert result == []


class TestFirebaseClientSendNotification:
    def test_send_notification_returns_true_when_available(self, mock_firebase_admin):
        stub, cred_path = mock_firebase_admin
        stub._apps = {}  # type: ignore[attr-defined]
        from src.firebase_client import FirebaseClient

        client = FirebaseClient(
            credentials_path=cred_path,
            storage_bucket="test.appspot.com",
        )
        result = client.send_notification(
            "alert_001",
            {
                "activity": "Weapon Detected",
                "activity_type": "weapon",
                "confidence": 0.91,
                "location": "ATM Entrance",
            },
        )
        assert result is True

    def test_send_notification_returns_false_when_unavailable(self, mock_firebase_admin):
        _stub, _cred_path = mock_firebase_admin
        from src.firebase_client import FirebaseClient

        client = FirebaseClient(
            credentials_path="/nonexistent/creds.json",
            storage_bucket="test.appspot.com",
        )
        result = client.send_notification("alert_001", {})
        assert result is False


class TestAlertManagerFirebaseIntegration:
    """Test AlertManager with a mocked FirebaseClient."""

    def test_create_alert_pushes_to_firebase(self, mock_firebase_admin, tmp_path):
        import time

        from src.activity_analyzer import ActivityEvent
        from src.alert_manager import AlertManager

        mock_fb = MagicMock()
        mock_fb.create_alert = MagicMock(return_value="alert_test_fb_001")

        am = AlertManager(
            db_path=str(tmp_path / "alerts.db"),
            snapshot_dir=str(tmp_path / "snapshots"),
            firebase_client=mock_fb,
        )

        event = ActivityEvent(
            activity="Weapon Detected",
            activity_type="weapon",
            detected_object="gun",
            confidence=0.91,
            timestamp=time.time(),
            person_id=1,
            bbox=(10, 20, 80, 150),
            zone_name="atm_zone",
            metadata={},
        )

        alert = am.create_alert(event)
        assert alert["activity_type"] == "weapon"
        mock_fb.create_alert.assert_called_once()

    def test_create_alert_works_without_firebase(self, tmp_path):
        import time

        from src.activity_analyzer import ActivityEvent
        from src.alert_manager import AlertManager

        am = AlertManager(
            db_path=str(tmp_path / "alerts.db"),
            snapshot_dir=str(tmp_path / "snapshots"),
            firebase_client=None,
        )

        event = ActivityEvent(
            activity="Loitering Detected",
            activity_type="loitering",
            detected_object=None,
            confidence=1.0,
            timestamp=time.time(),
            person_id=2,
            bbox=(0, 0, 50, 100),
            zone_name="queue_zone",
            metadata={},
        )

        alert = am.create_alert(event)
        assert alert["activity_type"] == "loitering"
