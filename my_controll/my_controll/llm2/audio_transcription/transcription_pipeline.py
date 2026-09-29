from __future__ import annotations
import time
import numpy as np
from dataclasses import dataclass

from .audio_source import AudioSourceDevice, AudioSourceDeviceConfig
from .transcriptor import Transcriptor, TranscriptorConfig
import math

from ..base.pipeline import Pipeline, PipelineConfig
from ..data_handling.schemas import TranscriptResult
from ..utils.audio_processing import flatten_chunk, check_for_speech, noise_reduction


@dataclass(frozen=True)
class SpeechTranscriptionPipelineConfig(PipelineConfig):
    """
    Configuration for a speech transcription pipeline.

    Parameters
    ---
    audio_source_device_config : AudioSourceDeviceConfig
            Configuration item for the audio source to read from.
    transcriptor_config : TranscriptorConfig
        Configuration item for the model to transcribe text with.
    activation_threshold : float (default = 0.01)
        Audio intensity threshold to determine if a chunk is likely
        to contain speech and thus be processed.
    cutoff_frequency : float (default = 0.01)
        High-pass cutoff in cycles per sample, between 0 and 0.5.
        At 16000 samples per second, 0.01 corresponds to 160 Hz.
    silence_patience : int (default = 25)
        Number of silent chunks before an utterance is considered finished.
    min_audio_seconds : float (default = 0.8)
        Minimum seconds for an utterance to be considered valid.
    max_buffer_size : int (default = 100)
        Maximum size of the speech buffer before forcefully processed.
        If this size is reached, some overlap will be included in the next
        buffer to account for split words.
    overlap_on_full_buffer : int (default = 10)
        How much overlap to include in the new speech buffer
        if the previous buffer was processed because of filling up.
    """
    audio_source_device_config: AudioSourceDeviceConfig
    transcriptor_config: TranscriptorConfig
    activation_threshold: float = 0.01
    cutoff_frequency: float = 0.01
    silence_patience: int = 25
    min_audio_seconds: float = 0.8
    max_buffer_size: int = 100
    overlap_on_full_buffer: int = 10

    def __post_init__(self):
        if not isinstance(self.audio_source_device_config, AudioSourceDeviceConfig):
            raise TypeError("Invalid audio source configuration.")
        if not isinstance(self.transcriptor_config, TranscriptorConfig):
            raise TypeError("Invalid transcriptor configuration.")
        if self.audio_source_device_config.sample_rate != 16000:
            raise ValueError("Whisper requires audio sampled at 16000 Hz.")
        for name in ("activation_threshold", "cutoff_frequency", "min_audio_seconds"):
            value = getattr(self, name)
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value < 0):
                raise ValueError(f"{name} must be finite and nonnegative.")
        if self.activation_threshold == 0 or self.min_audio_seconds == 0:
            raise ValueError("Speech threshold and minimum duration must be positive.")
        if self.cutoff_frequency > 0.5:
            raise ValueError("Cutoff frequency must be between 0 and 0.5.")
        for name in ("silence_patience", "max_buffer_size"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer.")
        if (type(self.overlap_on_full_buffer) is not int
                or not 0 <= self.overlap_on_full_buffer < self.max_buffer_size):
            raise ValueError("Overlap must be nonnegative and smaller than the buffer.")


class SpeechTranscriptionPipeline(Pipeline[SpeechTranscriptionPipelineConfig]):
    config_class = SpeechTranscriptionPipelineConfig

    def __init__(self, config:SpeechTranscriptionPipelineConfig):
        super().__init__(config)
        # Create sub-components
        self._audio_source = AudioSourceDevice(
            self.config.audio_source_device_config
        )
        self._transcriptor = Transcriptor(
            self.config.transcriptor_config
        )
        # Initialize buffer and state variables
        self._speech_buffer = []
        self._silence_counter = 0
        self._speaking = False
        self._new_speech = False
        self._utterance_segmented = False
        # Minimum chunks calc and validation
        self._min_chunks = int(np.ceil(
            self.config.min_audio_seconds / self._audio_source.get_chunk_duration()
        ))
        if self._min_chunks > self.config.max_buffer_size:
            raise ValueError(
                "Buffer size insufficient for minimum speech duration."
            )

    # === OVERRIDES ===

    def _do_start(self):
        self._clear_state()
        self._transcriptor.start()
        self._audio_source.start()

    def _do_run(self)->TranscriptResult:
        """Processes one available audio chunk from the source."""
        # The pipeline handles paused states
        # by bypassing the audio read
        if self.is_paused:
            return TranscriptResult()
        # Grab audio from source and begin processing
        chunk = self._audio_source.run()
        if chunk is None:
            return TranscriptResult()
        mono_chunk = flatten_chunk(chunk)
        if mono_chunk.size == 0:
            return TranscriptResult()
        metadata = {"speech_detected": False, "done_speaking": False,
                    "utterance_complete": False}
        speech_detected = check_for_speech(
            mono_chunk,
            self.config.activation_threshold
        )
        metadata["speech_detected"] = speech_detected
        # If there's speech in this chunk
        if speech_detected:
            self._silence_counter = 0
            self._speaking = True
            self._new_speech = True
            filtered_chunk = noise_reduction(mono_chunk, self.config.cutoff_frequency)
            self._speech_buffer.append(filtered_chunk)
        # If there's no speech but patience hasn't been reached yet
        elif self._speaking:
            self._silence_counter += 1
            filtered_chunk = noise_reduction(mono_chunk, self.config.cutoff_frequency)
            self._speech_buffer.append(filtered_chunk)
            # Check if patience has been reached
            if self._silence_counter >= self.config.silence_patience:
                self._speaking = False
                self._silence_counter = 0
                metadata["done_speaking"] = True
                metadata["utterance_complete"] = True
                result = self._transcribe()  # No overlap
                self._utterance_segmented = False
                return TranscriptResult(
                    result.text,
                    {**result.metadata, **metadata}
                )
        # Logic for when buffer is full
        if len(self._speech_buffer) >= self.config.max_buffer_size:
            result = self._transcribe(
                overlap=self.config.overlap_on_full_buffer
            )
            self._utterance_segmented = True
            return TranscriptResult(
                result.text,
                {**result.metadata, **metadata}
            )
        # Empty chunks
        return TranscriptResult(metadata=metadata)

    def _do_close(self):
        try:
            self._audio_source.close()
        finally:
            try:
                self._transcriptor.close()
            finally:
                self._clear_state()

    # === PIPELINE OVERRIDES ===

    def _do_pause(self):
        self._audio_source.close()
        self._clear_state()

    def _do_resume(self):
        self._clear_state()
        self._audio_source.start()

    # === HELPERS ===

    def _clear_state(self):
        self._speech_buffer = []
        self._silence_counter = 0
        self._speaking = False
        self._new_speech = False
        self._utterance_segmented = False
        if self._audio_source.is_started:
            self._audio_source.clear_buffer()

    def _transcribe(self, overlap:int=0)->TranscriptResult:
        """Transcribes content in the buffer and clears it."""
        n_chunks = len(self._speech_buffer)
        # If there's no speech or insufficient chunks
        if (
            n_chunks == 0
            or not self._new_speech
            or (n_chunks < self._min_chunks and not self._utterance_segmented)
        ):
            self._speech_buffer = []
            self._new_speech = False
            return TranscriptResult()
        # If there's something to transcribe
        audio = np.concatenate(self._speech_buffer)
        self._new_speech = False
        # Handle overlap
        if overlap > 0:
            self._speech_buffer = self._speech_buffer[-min(overlap, n_chunks):]
        else:
            self._speech_buffer = []
        # Transcribe text
        start_time = time.monotonic_ns()
        transcription = self._transcriptor.run(audio)
        end_time = time.monotonic_ns()
        return TranscriptResult(
            transcription,
            {"time_taken_seconds": (end_time - start_time) / 1e9}
        )

    def has_pending_speech(self):
        return self._speaking or self._new_speech

    process_chunk = Pipeline.run
