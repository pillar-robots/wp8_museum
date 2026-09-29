#!/usr/bin/env python3
"""Public, synchronous conversation entry point."""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from threading import Event, Lock
from typing import Optional
import rclpy
from rclpy.node import Node
from my_controll.llm2.conversation_pipeline import ConversationPipeline
from my_controll.llm2 import settings
from my_controll.llm2.utils.text_processing import trim_unfinished_sentence
from my_controll.public_speech_policy import TextToSpeechNode


class Conversation(Node):
    sentence_end_chars = (".", "!", "?")
    stop_kwrds = settings.STOP_KEYWORDS

    def __init__(self, *, pipeline=None, speaker=None, on_text=None, run_options=None):
        super().__init__("conversation")
        self.tts = TextToSpeechNode()
        self.sink = speaker if speaker is not None else self.tts.call_speech
        self.on_text = on_text
        self.conversation = pipeline if pipeline is not None else ConversationPipeline(
            transcription_pipeline_config=settings.TRANSCRIPTION_PIPELINE_CONFIG,
            model_config=settings.MODEL_CONFIG,
            idle_sleep_seconds=settings.IDLE_SLEEP_SECONDS,
        )
        self.speech_limit = settings.SPEECH_LIMIT
        self._run_options = dict(run_options or {})
        self._is_running = False
        self._launch_lock = Lock()
        self._stop = Event()

    def launch(self, state_path: Optional[Path] = None):
        self._launch(state_path, {})

    def begin_conversation(self, state_path=None, **options):
        self._launch(state_path, options)

    def _launch(self, state_path, overrides):
        if not self._launch_lock.acquire(blocking=False):
            raise RuntimeError("Conversation already running.")
        self._is_running = True
        responses = None
        loaded = False
        try:
            if self._stop.is_set():
                return
            state_path = Path(state_path) if state_path is not None else None
            if state_path is not None and state_path.exists():
                self.conversation.load_state(state_path)
            loaded = True
            self.conversation.start()
            # start() resets the pipeline's stop event, so repeat cancellation.
            if self._stop.is_set():
                self.conversation.request_stop()
            options = {
                "stop_kwrds": settings.STOP_KEYWORDS,
                "silence_seconds": settings.PUBLIC_SLEEP_SECONDS_TO_SHUTDOWN,
                "est_word_time": settings.ESTIMATED_WORD_UTTERANCE_TIME_SECONDS,
                "initial_prompt": (
                    settings.PUBLIC_INITIAL_PROMPT 
                    if state_path is not None else None
                ),
                **self._run_options, **overrides,
                "speaker": self.sink,
            }
            self.conversation.reset_speech_counter()
            responses = self.conversation.run(**options)
            print("Ready to talk!")
            for response in responses:
                # Playback happens inside the pipeline while capture is paused.
                text, speech_counter = response
                if self.on_text is not None:
                    self.on_text(text)
                
                if speech_counter >= self.speech_limit:
                    return
        finally:
            active_error = sys.exc_info()[0] is not None
            errors = []
            try:
                actions = []
                if responses is not None:
                    actions.append(responses.close)
                actions.append(self.conversation.close)
                if loaded and state_path is not None:
                    actions.append(lambda: self.conversation.save_state(state_path))
                for action in actions:
                    try:
                        action()
                    except Exception as error:
                        errors.append(error)
                        if active_error:
                            logging.getLogger(__name__).exception("Conversation cleanup failed.")
            finally:
                self._is_running = False
                self._stop.clear()
                self._launch_lock.release()
            if errors and not active_error:
                raise errors[0]

    def request_stop(self):
        """Cooperatively stop without closing resources used by generation."""
        self._stop.set()
        self.conversation.request_stop()

    def destroy_node(self):
        self.request_stop()
        if not self._is_running:
            self.conversation.close()
        return super().destroy_node()


def main(args=None):
    rclpy.init()
    node = Conversation()
    node.launch(state_path=settings.STATE_PATH)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
