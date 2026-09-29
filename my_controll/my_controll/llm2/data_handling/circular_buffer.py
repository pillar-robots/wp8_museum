"""Bounded, preallocated audio queue with consistent cross-thread reads."""
from threading import Lock
from typing import Optional, Tuple
import numpy as np


class CircularBuffer:
    def __init__(self, max_size: int, item_shape: Tuple[int, int]):
        if type(max_size) is not int or max_size <= 0:
            raise ValueError("Buffer size must be a positive integer.")
        if not item_shape or any(type(n) is not int or n <= 0 for n in item_shape):
            raise ValueError("Buffer dimensions must be positive integers.")
        self.max_chunks = max_size
        self.buffer = np.zeros((max_size, *item_shape), dtype=np.float32)
        self._write_count = 0
        self._read_count = 0
        self._lock = Lock()

    def put(self, item: np.ndarray):
        if item.shape != self.buffer.shape[1:]:
            raise ValueError("Audio chunk shape does not match the buffer.")
        # PortAudio must never block behind the consumer. Drop this chunk if busy.
        if not self._lock.acquire(blocking=False):
            return
        try:
            self.buffer[self._write_count % self.max_chunks] = item
            self._write_count += 1
        finally:
            self._lock.release()

    def get(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._write_count == self._read_count:
                return None
            self._read_count = max(self._read_count, self._write_count - self.max_chunks)
            item = self.buffer[self._read_count % self.max_chunks].copy()
            self._read_count += 1
            return item

    def clear(self):
        with self._lock:
            self._read_count = self._write_count
