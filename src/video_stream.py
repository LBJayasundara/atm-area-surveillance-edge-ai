"""
RTSP video stream handler with automatic reconnection logic.

Reads frames from an IP CCTV camera in a background thread and
provides the latest frame for the main detection pipeline.
"""

import threading
import time
from typing import Optional, Tuple

import cv2
import numpy as np

from src.logger import get_logger

logger = get_logger(__name__)


class VideoStream:
    """Thread-safe RTSP video stream reader with reconnect support."""

    def __init__(
        self,
        rtsp_url: str,
        width: int = 1280,
        height: int = 720,
        fps: int = 15,
        reconnect_delay: float = 5.0,
        max_reconnect_attempts: int = 10,
    ) -> None:
        """
        Initialise the video stream.

        Args:
            rtsp_url: RTSP URL of the IP camera.
            width: Desired frame width in pixels.
            height: Desired frame height in pixels.
            fps: Desired frames per second.
            reconnect_delay: Seconds to wait before each reconnect attempt.
            max_reconnect_attempts: Maximum consecutive reconnect attempts before giving up.
        """
        self.rtsp_url = rtsp_url
        self.width = width
        self.height = height
        self.fps = fps
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts

        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._connected = False
        self._frame_count = 0
        self._reconnect_count = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Open the stream and start the background capture thread."""
        if self._running:
            logger.warning("VideoStream already running.")
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("VideoStream started for %s", self.rtsp_url)

    def stop(self) -> None:
        """Stop the capture thread and release resources."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=10)
        self._release_cap()
        logger.info("VideoStream stopped.")

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Return the most recent frame.

        Returns:
            Tuple of (success, frame). *success* is False when no frame is available.
        """
        with self._lock:
            if self._frame is None:
                return False, None
            return True, self._frame.copy()

    @property
    def is_connected(self) -> bool:
        """Whether the stream is currently connected."""
        return self._connected

    @property
    def frame_count(self) -> int:
        """Total number of frames captured since start."""
        return self._frame_count

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _open_stream(self) -> bool:
        """Attempt to open the RTSP stream.

        Returns:
            True on success, False on failure.
        """
        self._release_cap()
        try:
            self._cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self._cap.set(cv2.CAP_PROP_FPS, self.fps)
            # Reduce buffer size to minimise latency
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if self._cap.isOpened():
                self._connected = True
                self._reconnect_count = 0
                logger.info("Connected to RTSP stream: %s", self.rtsp_url)
                return True
            logger.error("Failed to open RTSP stream: %s", self.rtsp_url)
            return False
        except Exception as exc:  # noqa: BLE001
            logger.error("Exception opening stream: %s", exc)
            return False

    def _release_cap(self) -> None:
        """Release the OpenCV capture object."""
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:  # noqa: BLE001
                pass
            self._cap = None
        self._connected = False

    def _capture_loop(self) -> None:
        """Background thread: continuously read frames, reconnect on failure."""
        while self._running:
            if not self._connected:
                if self._reconnect_count >= self.max_reconnect_attempts:
                    logger.critical(
                        "Max reconnect attempts (%d) reached. Stopping stream.",
                        self.max_reconnect_attempts,
                    )
                    self._running = False
                    break
                logger.info(
                    "Connecting to stream (attempt %d/%d)…",
                    self._reconnect_count + 1,
                    self.max_reconnect_attempts,
                )
                if not self._open_stream():
                    self._reconnect_count += 1
                    time.sleep(self.reconnect_delay)
                    continue

            ret, frame = self._cap.read()  # type: ignore[union-attr]
            if not ret or frame is None:
                logger.warning("Frame read failed — reconnecting…")
                self._connected = False
                self._reconnect_count += 1
                time.sleep(self.reconnect_delay)
                continue

            with self._lock:
                self._frame = frame
            self._frame_count += 1
