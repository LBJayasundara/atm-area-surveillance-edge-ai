"""
Performance optimisation utilities.

Provides:
- Frame-rate controller (frame skipping)
- Multi-threaded frame producer / consumer queue
- Performance monitor (FPS, latency, memory)
"""

from __future__ import annotations

import threading
import time
from collections import deque
from queue import Empty, Queue
from typing import Callable, Deque, Optional, Tuple

import numpy as np

from src.logger import get_logger

logger = get_logger(__name__)


class FrameRateController:
    """
    Limits processing frame rate by dropping frames when the pipeline
    falls behind.

    Usage::

        frc = FrameRateController(target_fps=8)
        while True:
            ret, frame = stream.read()
            if frc.should_process():
                detect(frame)
    """

    def __init__(self, target_fps: float = 8.0) -> None:
        self.target_fps = target_fps
        self._interval = 1.0 / max(target_fps, 1.0)
        self._last_process_time = 0.0

    def should_process(self) -> bool:
        """Return True if enough time has elapsed to process a new frame."""
        now = time.monotonic()
        if now - self._last_process_time >= self._interval:
            self._last_process_time = now
            return True
        return False


class FrameQueue:
    """
    Thread-safe single-item frame buffer.

    The producer always writes the *latest* frame; the consumer reads
    the latest available frame without blocking for old ones.
    """

    def __init__(self, maxsize: int = 2) -> None:
        self._queue: Queue = Queue(maxsize=maxsize)
        self._lock = threading.Lock()

    def put(self, frame: np.ndarray) -> None:
        """
        Put a frame into the queue, discarding oldest if full.

        Args:
            frame: BGR NumPy frame.
        """
        with self._lock:
            if self._queue.full():
                try:
                    self._queue.get_nowait()
                except Empty:
                    pass
            self._queue.put_nowait(frame)

    def get(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """
        Get the latest frame, or None if nothing is available.

        Args:
            timeout: Seconds to wait before returning None.

        Returns:
            Frame or None.
        """
        try:
            return self._queue.get(timeout=timeout)
        except Empty:
            return None


class PerformanceMonitor:
    """
    Tracks FPS, inference latency, and RSS memory usage.
    """

    def __init__(self, window: int = 30) -> None:
        """
        Initialise the monitor.

        Args:
            window: Number of recent samples to keep for rolling statistics.
        """
        self._timestamps: Deque[float] = deque(maxlen=window)
        self._latencies: Deque[float] = deque(maxlen=window)
        self._lock = threading.Lock()

    def record_frame(self, latency_ms: float) -> None:
        """
        Record a processed frame.

        Args:
            latency_ms: Inference+analysis latency for this frame in milliseconds.
        """
        with self._lock:
            self._timestamps.append(time.monotonic())
            self._latencies.append(latency_ms)

    @property
    def fps(self) -> float:
        """Rolling average frames-per-second."""
        with self._lock:
            if len(self._timestamps) < 2:
                return 0.0
            elapsed = self._timestamps[-1] - self._timestamps[0]
            if elapsed <= 0:
                return 0.0
            return (len(self._timestamps) - 1) / elapsed

    @property
    def avg_latency_ms(self) -> float:
        """Rolling average inference latency in milliseconds."""
        with self._lock:
            if not self._latencies:
                return 0.0
            return sum(self._latencies) / len(self._latencies)

    @property
    def memory_mb(self) -> float:
        """Current process RSS memory in megabytes."""
        try:
            import resource
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        except Exception:  # noqa: BLE001
            try:
                import psutil
                import os
                return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
            except Exception:  # noqa: BLE001
                return 0.0

    def summary(self) -> dict:
        """Return a performance summary dictionary."""
        return {
            "fps": round(self.fps, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "memory_mb": round(self.memory_mb, 1),
        }
