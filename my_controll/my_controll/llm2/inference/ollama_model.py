from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
import math
from typing import Any, Dict, Optional

from ollama import Client

from ..base import Component, ComponentConfig
from ..utils.text_processing import unwrap_model_response, trim_unfinished_sentence
from .model_state_manager import ModelStateManager


@dataclass(frozen=True)
class OllamaModelConfig(ComponentConfig):
    """
    Config for an Ollama Model.

    Parameters
    ---
    model_name:
        Ollama model tag, for example 'llama3.2:3b'.
    host:
        Optional Ollama server URL. The client default is used when omitted.
    client:
        Optional compatible client with show, chat, and generate methods,
        plus pull when downloading models.
        Injected clients remain owned by their caller and are not closed here.
    system_instructions : str
        System prompt for the model.
    options : Dict[str, Any]
        Generation options.
    request_timeout : float (default = 300.0)
        HTTP timeout in seconds, including waiting for a complete response.
        An injected client controls its own timeout settings.
    """
    model_name: str
    host: Optional[str] = None
    client: Any = None
    system_instructions: str = ""
    options: Dict[str, Any] = field(default_factory=dict)
    request_timeout: float = 300.0

    def __post_init__(self):
        if not isinstance(self.model_name, str) or not self.model_name.strip():
            raise ValueError("Model name must be a non-empty string.")
        if not isinstance(self.system_instructions, str):
            raise TypeError("System instructions must be a string.")
        if not isinstance(self.options, dict):
            raise TypeError("Options must be a dictionary.")
        if (isinstance(self.request_timeout, bool)
                or not isinstance(self.request_timeout, (int, float))
                or not math.isfinite(self.request_timeout) or self.request_timeout <= 0):
            raise ValueError("Request timeout must be finite and positive.")


class OllamaModel(Component[OllamaModelConfig]):
    config_class = OllamaModelConfig

    def __init__(self, config:OllamaModelConfig):
        super().__init__(config)
        self._client = self.config.client
        self._owns_client = self._client is None
        # Initialize state manager
        self._state = ModelStateManager(
            model_name=self.config.model_name,
            system_instructions=self.config.system_instructions
        )

    # === COMPONENT OVERRIDES ===

    def _do_start(self):
        if self._owns_client:
            self._client = Client(
                host=self.config.host, timeout=self.config.request_timeout
            )
        try:
            self._load_model()
        except BaseException:
            if self._owns_client:
                client, self._client = self._client, None
                try:
                    client.close()
                except Exception:
                    import logging
                    logging.getLogger(__name__).exception("Failed to close Ollama client.")
            raise

    def _do_run(
            self,
            prompt:str,
            options:Any=None,
    )->str:
        return self._generate(prompt, options)

    def _do_close(self):
        if self._client is None:
            return
        try:
            self._client.generate(  # This terminates the model
                model=self.config.model_name,
                prompt="",
                keep_alive=0,
                stream=False,
            )
        finally:
            if self._owns_client:
                try:
                    self._client.close()
                finally:
                    self._client = None

    # === GENERATION ===

    def _generate(self, prompt:str, options:Any = None) -> str:
        out = self._call_model(prompt, options)
        done = out.get("done", True) if isinstance(out, Mapping) else getattr(out, "done", True)
        if done is not True:
            raise RuntimeError("Model returned an incomplete response.")
        text = unwrap_model_response(out)
        trimmed = trim_unfinished_sentence(text)
        self._state.add_turn(prompt, trimmed)
        return trimmed

    def _call_model(
            self,
            prompt:str,
            options:Any=None
    ):
        if not isinstance(prompt, str):
            raise TypeError("Prompt must be a string.")
        if not prompt.strip():
            raise ValueError("Prompt cannot be an empty string.")
        # Use given options or defaults
        generation_options = self.config.options if options is None else options
        # Build API payload using the state manager
        msg_payload = self._state.build_payload(prompt)
        return self._client.chat(
            model=self.config.model_name,
            messages=msg_payload,
            options=generation_options,
            stream=False,
        )

    # === UTILITIES ===

    def generate(self, prompt, options=None):
        """Compatibility alias for complete, non-streaming generation."""
        return self.run(prompt, options)

    def get_state(self):
        return self._state.get_state()

    def set_state(self, state):
        if self.is_started:
            raise RuntimeError("Stop the model before restoring state.")
        self._state.set_state(state)

    def get_history(self):
        return [asdict(message) for message in self.get_state().messages]

    def set_history(self, messages):
        self._state.set_history(messages)

    def set_system_instructions(self, instructions):
        self._state.set_system_instructions(instructions)

    def download(self):
        client = (
            Client(host=self.config.host, timeout=self.config.request_timeout)
            if self._owns_client else self._client
        )
        try:
            client.pull(model=self.config.model_name, stream=False)
        except Exception as e:
            raise RuntimeError(
                f"Could not download model '{self.config.model_name}'."
            ) from e
        finally:
            if self._owns_client:
                client.close()

    def _load_model(self):
        try:
            self._client.show(self.config.model_name)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            raise RuntimeError(
                f"Could not load model '{self.config.model_name}'. Ensure the "
                "Ollama server is running and the model is installed."
            ) from e
