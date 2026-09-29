from __future__ import annotations

import inspect
import json
import logging
import math
import os
import sys
import tempfile
import time
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import Future
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Any, Union
from threading import Event, Lock

from .base.pipeline import Pipeline, PipelineConfig
from .audio_transcription import SpeechTranscriptionPipeline
from .inference import OllamaModel
from .data_handling.schemas import OllamaModelState
from .utils.text_processing import normalize_text, prepare_keywords, merge_transcript, trim_unfinished_sentence


@dataclass(frozen=True)
class ConversationPipelineConfig(PipelineConfig):
    """
    Configuration for the Conversation Pipeline.
    """
    transcription_pipeline: SpeechTranscriptionPipeline
    model: OllamaModel
    idle_sleep_seconds: float = 0.01


class ConversationPipeline(Pipeline[ConversationPipelineConfig]):
    config_class = ConversationPipelineConfig

    def __init__(self, config=None, model_config=None, idle_sleep_seconds=0.01,
                 *, transcription_pipeline_config=None):
        # Keep the previous positional/configuration-keyword construction usable.
        if transcription_pipeline_config is not None:
            if config is not None:
                raise TypeError("Specify only one transcription configuration.")
            config = transcription_pipeline_config
        if not isinstance(config, ConversationPipelineConfig):
            if config is None or model_config is None:
                raise TypeError("Transcription and model configurations are required.")
            config = ConversationPipelineConfig(
                SpeechTranscriptionPipeline(config), OllamaModel(model_config),
                idle_sleep_seconds,
            )
        super().__init__(config)

        if (isinstance(self.config.idle_sleep_seconds, bool)
                or not isinstance(self.config.idle_sleep_seconds, (int, float))
                or not math.isfinite(self.config.idle_sleep_seconds)
                or self.config.idle_sleep_seconds <= 0):
            raise ValueError("Idle sleep seconds must be finite and positive.")

        self._transcription_pipeline = self.config.transcription_pipeline
        self._model = self.config.model

        # State tracking
        self._is_running = False
        self._stop_requested = Event()
        self._run_lock = Lock()
        self.stop_reason = None
        self._speech_counter = 0

    # === PIPELINE LIFECYCLE OVERRIDES ===

    def _do_start(
            self,
            download_language_model: bool = False,
            *args, **kwargs
    ):
        self._stop_requested.clear()
        self.stop_reason = None
        if download_language_model:
            self._model.download()
        self._model.start()
        self._transcription_pipeline.start()

    def _do_close(self, *args, **kwargs):
        self.request_stop()
        try:
            self._transcription_pipeline.close()
        finally:
            self._model.close()

    def _do_pause(self, *args, **kwargs):
        self._transcription_pipeline.pause()

    def _do_resume(self, *args, **kwargs):
        self._transcription_pipeline.resume()

    # === CORE EXECUTION ===

    def _pause_transcription_and_generate(
            self,
            prompt: str,
            speaker: Optional[Callable[[str], Any]] = None,
            est_word_time: float = 0.4,
    ) -> str:
        """
        Pauses transcription, generates a complete response, triggers playback,
        and resumes listening. Returns the complete generated text.
        """
        self.pause()
        output = ""
        completed = False

        try:
            # Standard autoregressive generation
            output = self._model.run(prompt)

            if output and speaker is not None and not self._stop_requested.is_set():
                completion = speaker(output)
                if isinstance(completion, Future):
                    completion.result()
                elif inspect.isawaitable(completion):
                    if inspect.iscoroutine(completion):
                        completion.close()
                    raise TypeError("Speaker must block until playback finishes.")
                elif completion is not None:
                    raise TypeError("Speaker must return None or a playback Future.")
            time.sleep(est_word_time * len(output.split()))
            print("Resuming")
            completed = True
            return output

        finally:
            if completed and not self._stop_requested.is_set():
                self.resume()

    def _do_run(
            self,
            stop_kwrds: Optional[Sequence[str]] = None,
            silence_seconds: Optional[float] = None,
            est_word_time: Optional[float] = 0.1,
            speaker: Optional[Callable[[str], Any]] = None,
            initial_prompt: Optional[str] = None,
            *args, **kwargs
    ) -> Iterator[str]:
        """Yield full responses until a stop phrase, silence, or stop request.

        Consume or close the iterator to complete cleanup. A speaker must block
        until playback ends or return a concurrent.futures.Future for playback.
        est_word_time is accepted for compatibility; actual playback completion
        determines when the silence timer starts.
        """
        if not self._run_lock.acquire(blocking=False):
            raise RuntimeError("A conversation is already running.")

        self._is_running = True
        try:
            if not self.is_started:
                raise RuntimeError("Start the conversation before consuming responses.")
            keywords = prepare_keywords(stop_kwrds)
            # Retained for caller compatibility. Playback completion controls timing.
            if est_word_time is not None and (
                    isinstance(est_word_time, bool)
                    or not isinstance(est_word_time, (int, float))
                    or not math.isfinite(est_word_time) or est_word_time < 0):
                raise ValueError("Estimated word time must be finite and nonnegative.")

            if silence_seconds is not None:
                if (isinstance(silence_seconds, bool)
                        or not isinstance(silence_seconds, (int, float))
                        or not math.isfinite(silence_seconds)
                        or silence_seconds <= 0):
                    raise ValueError("Silence seconds must be finite and positive.")

            if speaker is not None and not callable(speaker):
                raise TypeError("Speaker must be callable.")

            if initial_prompt is not None:
                if not isinstance(initial_prompt, str) or not initial_prompt.strip():
                    raise ValueError("Initial prompt must be a non-empty string.")
                if not self._stop_requested.is_set():
                    output = self._pause_transcription_and_generate(
                        initial_prompt, speaker, est_word_time
                    )
                    if output:
                        yield output, self.increase_speech_counter()

            est_idle_time = time.monotonic()
            pending_text = ""

            while not self._stop_requested.is_set():
                result = self._transcription_pipeline.run()
                if self._stop_requested.is_set():
                    break
                now = time.monotonic()
                spoken_text = result.text.strip()

                if result.metadata.get("speech_detected") or spoken_text:
                    est_idle_time = now

                if spoken_text:
                    if self._transcription_pipeline.config.overlap_on_full_buffer:
                        pending_text = merge_transcript(pending_text, spoken_text)
                    else:
                        pending_text = " ".join(filter(None, (pending_text, spoken_text)))

                    normalized_text = " " + normalize_text(pending_text) + " "
                    if any(keyword in normalized_text for keyword in keywords):
                        self.stop_reason = "keyword"
                        return

                utterance_complete = result.metadata.get("utterance_complete", bool(spoken_text))
                if pending_text and utterance_complete:
                    output = self._pause_transcription_and_generate(
                        pending_text, speaker, est_word_time
                    )
                    if output:
                        yield output, self.increase_speech_counter()

                    pending_text = ""
                    est_idle_time = time.monotonic()

                elif (silence_seconds is not None
                        and not self._transcription_pipeline.has_pending_speech()
                        and now - est_idle_time >= silence_seconds):
                    self.stop_reason = "silence"
                    return
                else:
                    # A stop request wakes idle polling immediately.
                    self._stop_requested.wait(self.config.idle_sleep_seconds)

            self.stop_reason = "requested"

        finally:
            self._is_running = False
            try:
                if sys.exc_info()[0] is not None:
                    try:
                        self.close()
                    except Exception:
                        logging.getLogger(__name__).exception("Conversation cleanup failed.")
                else:
                    self.close()
            finally:
                self._run_lock.release()

    def request_stop(self):
        self._stop_requested.set()

    # === STATE MANAGEMENT ===

    def get_state(self)->OllamaModelState:
        return self._model.get_state()

    def set_state(self, state:OllamaModelState):
        if self.is_started or self._is_running:
            raise RuntimeError(
                "Stop the pipeline before restoring conversation state."
            )
        self._model.set_state(state)

    def save_state(self, path:Union[str,Path]):
        path = Path(path)
        state_dict = asdict(self.get_state())

        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", dir=path.parent,
                    prefix="." + path.name + ".", suffix=".tmp", delete=False,
                    ) as output:
                temporary_path = Path(output.name)
                json.dump(state_dict, output, ensure_ascii=False, indent=2)
                output.write("\n")
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def load_state(self, path: str | Path):
        with Path(path).open(encoding="utf-8") as saved_state:
            state_dict = json.load(saved_state)

        self.set_state(state_dict)

    def increase_speech_counter(self):
        self._speech_counter += 1
        return self._speech_counter

    def reset_speech_counter(self):
        self._speech_counter = 0