from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

if __package__.startswith("src."):
    from ..base import ComponentConfig, Component
    from ..utils.path_handling import make_model_dir
else:
    from ..base import ComponentConfig, Component
    from ..utils.path_handling import make_model_dir


@dataclass(frozen=True)
class TranscriptorConfig(ComponentConfig):
    """
    Settings for a Transcriptor.

    Attributes
    ---
    storage_dir : str
        Local model directory, or parent storage directory when using
        download_model() before startup.
    device : str (default = 'cpu')
        CTranslate2 runtime device, such as 'cuda' or 'cpu'.
    dtype : str (default = 'int8')
        Numeric precision to use (if supported). For instance, 'float16'.
    language : str
        Language hint passed to ASR providers.
    beam_size : int
        Decoding beam width for providers that expose beam search.
    """
    # Load settings
    storage_dir:str
    # Runtime settings
    device:str = "cpu"
    dtype:str = "int8"
    # Model settings
    language:str = "en"
    beam_size:int = 5
    model_kwargs:Any=field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.storage_dir, str) or not self.storage_dir.strip():
            raise ValueError("Storage directory must be a non-empty string.")
        if type(self.beam_size) is not int or self.beam_size <= 0:
            raise ValueError("Beam size must be a positive integer.")
        if not isinstance(self.model_kwargs, dict):
            raise TypeError("Model kwargs must be a dictionary.")
        if {"device", "compute_type", "local_files_only"} & self.model_kwargs.keys():
            raise ValueError("Use the dedicated configuration fields for model loading.")


class Transcriptor(Component[TranscriptorConfig]):
    config_class = TranscriptorConfig

    def __init__(self, config:TranscriptorConfig):
        super().__init__(config)
        # This is started in the start method
        self._model = None
        # Extract this class as it changes
        self._path = self.config.storage_dir

    # === ABSTRACT METHOD OVERRIDES ===

    def _do_start(self):
        from faster_whisper import WhisperModel
        self._model = WhisperModel(
            self._path,
            device=self.config.device,
            compute_type=self.config.dtype,
            local_files_only=True,
            **self.config.model_kwargs
        )

    def _do_run(self, audio:np.ndarray)->str:
        if audio is None:
            return ""
        audio = np.asarray(audio, dtype=np.float32)
        if audio.ndim != 1 or not np.all(np.isfinite(audio)):
            raise ValueError("Transcription requires finite mono samples.")
        if audio.size == 0:
            return ""
        segments, _ = self._model.transcribe(
            audio,
            language=self.config.language,
            beam_size=self.config.beam_size,
            vad_filter=True,
        )
        # transcribe returns a generator so concatenate outputs
        return " ".join(segment.text.strip() for segment in segments).strip()

    def _do_close(self):
        if self._model is not None:
            try:
                self._model.model.unload_model()
            finally:
                self._model = None

    # === UTILITIES ===

    def download_model(self, model_id, token=None):
        from faster_whisper.utils import download_model
        if self.is_started:
            raise RuntimeError(
                "Cannot download a new model while one is running."
            )
        self._path = download_model(
            model_id,
            output_dir=make_model_dir(
                model_id,
                self._path
            ),
            use_auth_token=token,
        )

    transcribe = Component.run
