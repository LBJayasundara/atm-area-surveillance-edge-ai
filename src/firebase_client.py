"""
Firebase Admin SDK client wrapper.

Provides Firestore and Firebase Storage operations for the ATM surveillance
system running on the Raspberry Pi edge device.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# firebase_admin is an optional dependency; the system falls back gracefully
# when it is not installed or credentials are unavailable.
try:
    import firebase_admin
    from firebase_admin import credentials, firestore, messaging, storage

    _FIREBASE_AVAILABLE = True
except ImportError:  # pragma: no cover
    _FIREBASE_AVAILABLE = False
    logger.warning(
        "firebase-admin package not installed. Firebase integration disabled."
    )


class FirebaseClient:
    """
    Wrapper around the Firebase Admin SDK for Firestore and Storage.

    All public methods handle errors internally and log warnings rather than
    raising exceptions, so the edge-AI pipeline continues running even when
    Firebase is temporarily unavailable.

    Args:
        credentials_path: Path to the Firebase service account JSON key file.
        storage_bucket: Firebase Storage bucket name
            (e.g. ``"your-project-id.appspot.com"``).
        collection_name: Firestore collection for alerts (default: ``"alerts"``).
        fcm_topic: FCM topic to publish alert notifications to
            (default: ``"atm_alerts"``).
    """

    def __init__(
        self,
        credentials_path: str,
        storage_bucket: str,
        collection_name: str = "alerts",
        fcm_topic: str = "atm_alerts",
    ) -> None:
        self._collection_name = collection_name
        self._fcm_topic = fcm_topic
        self._db: Optional[Any] = None
        self._bucket: Optional[Any] = None
        self._available = False

        if not _FIREBASE_AVAILABLE:
            logger.warning("Firebase Admin SDK unavailable — skipping init.")
            return

        if not os.path.isfile(credentials_path):
            logger.error(
                "Firebase credentials file not found: %s", credentials_path
            )
            return

        try:
            cred = credentials.Certificate(credentials_path)
            # Only initialise once per process (guard against hot-reloads).
            if not firebase_admin._apps:  # type: ignore[attr-defined]
                firebase_admin.initialize_app(
                    cred, {"storageBucket": storage_bucket}
                )
            self._db = firestore.client()
            self._bucket = storage.bucket()
            self._available = True
            logger.info("Firebase client initialised (bucket: %s).", storage_bucket)
        except Exception as exc:  # noqa: BLE001
            logger.error("Firebase initialisation failed: %s", exc)

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """Return True if the Firebase connection is active."""
        return self._available

    # ------------------------------------------------------------------
    # Alert operations
    # ------------------------------------------------------------------

    def create_alert(
        self,
        alert_data: Dict[str, Any],
        image_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Write a new alert document to Firestore and optionally upload an image.

        Args:
            alert_data: Alert dictionary following the project schema.
            image_path: Optional local path to the snapshot image to upload.

        Returns:
            Firestore document ID on success, or ``None`` on failure.
        """
        if not self._available:
            return None

        alert_id = alert_data.get("id") or (
            f"alert_{datetime.now(tz=timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            f"_{str(uuid.uuid4())[:8]}"
        )

        image_url = ""
        if image_path:
            image_url = self._upload_image(image_path, alert_id) or ""

        doc: Dict[str, Any] = {
            "alert_id": alert_id,
            "activity": alert_data.get("activity", ""),
            "activity_type": alert_data.get("activity_type", ""),
            "detected_object": alert_data.get("detected_object"),
            "confidence": alert_data.get("confidence", 0.0),
            "timestamp": firestore.SERVER_TIMESTAMP,
            "location": alert_data.get("location", ""),
            "image_url": image_url,
            "acknowledged": False,
            "metadata": alert_data.get("metadata", {}),
        }

        try:
            self._db.collection(self._collection_name).document(alert_id).set(doc)
            logger.info("Alert pushed to Firestore: %s", alert_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Firestore write failed for %s: %s", alert_id, exc)
            return None

        self.send_notification(alert_id, alert_data)
        return alert_id

    def update_alert(self, alert_id: str, updates: Dict[str, Any]) -> bool:
        """
        Partially update an existing alert document.

        Args:
            alert_id: Firestore document ID.
            updates: Field/value pairs to update.

        Returns:
            True on success, False on failure.
        """
        if not self._available:
            return False
        try:
            self._db.collection(self._collection_name).document(alert_id).update(
                updates
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Firestore update failed for %s: %s", alert_id, exc)
            return False

    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Mark an alert as acknowledged.

        Args:
            alert_id: Firestore document ID.

        Returns:
            True on success, False on failure.
        """
        return self.update_alert(
            alert_id,
            {
                "acknowledged": True,
                "acknowledged_at": firestore.SERVER_TIMESTAMP,
            },
        )

    def get_alerts(
        self,
        limit: int = 50,
        activity_type: Optional[str] = None,
    ) -> list[Dict[str, Any]]:
        """
        Retrieve recent alerts from Firestore.

        Args:
            limit: Maximum number of documents to return.
            activity_type: Optional filter by activity type.

        Returns:
            List of alert dictionaries, newest first.
        """
        if not self._available:
            return []
        try:
            query = self._db.collection(self._collection_name).order_by(
                "timestamp", direction=firestore.Query.DESCENDING
            )
            if activity_type:
                query = query.where("activity_type", "==", activity_type)
            query = query.limit(limit)
            return [doc.to_dict() for doc in query.stream()]
        except Exception as exc:  # noqa: BLE001
            logger.error("Firestore query failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # FCM notifications
    # ------------------------------------------------------------------

    def send_notification(
        self, alert_id: str, alert_data: Dict[str, Any]
    ) -> bool:
        """
        Send an FCM push notification to the configured topic.

        Args:
            alert_id: Alert identifier to include in the notification payload.
            alert_data: Alert dictionary used to compose the notification body.

        Returns:
            True if the message was accepted by FCM, False otherwise.
        """
        if not self._available or not _FIREBASE_AVAILABLE:
            return False
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=f"\U0001f6a8 {alert_data.get('activity', 'Suspicious Activity')}",
                    body=(
                        f"Confidence: {alert_data.get('confidence', 0):.0%} "
                        f"| {alert_data.get('location', '')}"
                    ),
                ),
                data={
                    "alert_id": alert_id,
                    "activity_type": alert_data.get("activity_type", ""),
                    "click_action": "FLUTTER_NOTIFICATION_CLICK",
                },
                topic=self._fcm_topic,
            )
            messaging.send(message)
            logger.debug("FCM notification sent for alert %s.", alert_id)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("FCM send failed for %s: %s", alert_id, exc)
            return False

    # ------------------------------------------------------------------
    # Storage helpers
    # ------------------------------------------------------------------

    def _upload_image(self, image_path: str, alert_id: str) -> Optional[str]:
        """
        Upload a snapshot image to Firebase Storage.

        Args:
            image_path: Local path to the JPEG image.
            alert_id: Used to derive the storage object name.

        Returns:
            Public URL of the uploaded image, or ``None`` on failure.
        """
        if self._bucket is None or not os.path.isfile(image_path):
            return None
        try:
            blob = self._bucket.blob(f"alerts/{alert_id}.jpg")
            blob.upload_from_filename(image_path, content_type="image/jpeg")
            blob.make_public()
            url: str = blob.public_url
            logger.debug("Image uploaded to Storage: %s", url)
            return url
        except Exception as exc:  # noqa: BLE001
            logger.warning("Storage upload failed for %s: %s", alert_id, exc)
            return None
