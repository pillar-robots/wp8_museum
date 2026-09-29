from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from typing import Any, Optional
import math

if __package__.startswith("src."):
    from ..base import Component, ComponentConfig
    from ..data_handling.circular_buffer import CircularBuffer
else:
    from ..base import Component, ComponentConfig
    from ..data_handling.circular_buffer import CircularBuffer


@dataclass(frozen=True)
class AudioSourceDeviceConfig(ComponentConfig):
    """
    Settings for an AudioSourceDevice.

    Parameters
    ---
    sample_rate : int (default = 16000)
        Number of audio samples captured per second.
    chunk_duration : float (default = 0.5)
        Seconds of audio stored in each bufferd chunk.
    channels : int (default = 1)
        Number of microphone channels requested from the backend.
    max_buffer_size : int (default = 100)
        Maximum buffered chunks before old audio is dropped.
    """
    device: Optional[int] = None
    sample_rate: int = 16000
    chunk_duration: float = 0.5
    channels: int = 1
    max_buffer_size: int = 100

    def __post_init__(self):
        for name in ("sample_rate", "channels", "max_buffer_size"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer.")
        if (isinstance(self.chunk_duration, bool)
                or not isinstance(self.chunk_duration, (int, float))
                or not math.isfinite(self.chunk_duration) or self.chunk_duration <= 0
                or int(self.sample_rate * self.chunk_duration) < 1):
            raise ValueError("Chunk duration must produce at least one sample.")


class AudioSourceDevice(Component[AudioSourceDeviceConfig]):
    config_class = AudioSourceDeviceConfig

    def __init__(self, config:AudioSourceDeviceConfig = AudioSourceDeviceConfig()):
        super().__init__(config)
        # Initialize self variables
        # Compute chunk size in frames : fps * s = frames
        self._chunk_size = int(self.config.sample_rate * self.config.chunk_duration)
        # This'll have to be started with the start method
        self._buffer = None
        self._stream = None

    # === ABSTRACT METHOD IMPLEMENTATIONS ===

    def _do_start(self):
        # Start buffer
        self._buffer = CircularBuffer(
            max_size=self.config.max_buffer_size,
            item_shape=(self._chunk_size, self.config.channels)
        )
        # Component.start handles partial startup without masking its error.
        self._stream = self._create_input_stream()
        self._stream.start()

    def _do_run(self)->Optional[np.ndarray]:
        """
        Read the next available microphone chunk.
        """
        # If backend is stopped always returns silence
        # so if there's no check it'd keep running
        if self._stream is None or not self._stream.active:
            self.close()
            raise RuntimeError("Microphone stream stopped unexpectedly.")
        return self._buffer.get()

    def _do_close(self):
        try:
            if self._stream is not None:
                self._stream.close()
        finally:
            self._stream = None
            self._buffer = None

    # === HELPERS ===

    def _create_input_stream(self):
        import sounddevice as sd
        return sd.InputStream(
            device=self.config.device,
            samplerate=self.config.sample_rate,
            blocksize=self._chunk_size,
            channels=self.config.channels,
            dtype="float32",
            callback=self._input_stream_callback,
        )

    def _input_stream_callback(
        self,
        indata:np.ndarray,
        # Parameters for compatibility with sd.InputStream callback
        frames:int,
        time:Any,
        status:Any,
    ):
        """
        buffer one chunk from the audio backend callback.
        Drops the oldest chunk when the buffer is full.
        """
        buffer = self._buffer
        if buffer is not None:
            buffer.put(indata)

    # === UTILITIES ===

    def clear_buffer(self) -> None:
        """Discard bufferd audio without closing the microphone stream."""
        if self._buffer is not None:
            self._buffer.clear()

    def get_chunk_duration(self)->float:
        """
        Returns the duration of a chunk in seconds.
        """
        return self._chunk_size / self.config.sample_rate

    read = Component.run
