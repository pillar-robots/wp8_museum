"""Validated, detached snapshots of completed conversation turns."""
from dataclasses import asdict
from typing import List

from ..data_handling.schemas import Message, OllamaModelState


class ModelStateManager:
    version = 1

    def __init__(self, model_name: str, system_instructions: str = ""):
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("Model name must be a non-empty string.")
        self._model_name = model_name
        self.set_system_instructions(system_instructions)
        self._history: List[Message] = []

    def set_system_instructions(self, new_instructions: str):
        if not isinstance(new_instructions, str):
            raise TypeError("System instructions must be a string.")
        self._system_instructions = new_instructions

    def set_history(self, messages):
        self._history = self._validate_history(messages)

    def add_turn(self, prompt: str, response: str):
        self._history.extend(self._validate_history([
            Message(role="user", content=prompt),
            Message(role="assistant", content=response),
        ]))

    @staticmethod
    def _validate_history(messages):
        if not isinstance(messages, list):
            raise TypeError("Conversation messages must be a list.")
        if len(messages) % 2:
            raise ValueError("Conversation history must contain complete turns.")
        validated = []
        for index, msg in enumerate(messages):
            if isinstance(msg, dict):
                if set(msg) != {"role", "content"}:
                    raise ValueError("Messages must contain role and content only.")
                msg = Message(**msg)
            if not isinstance(msg, Message):
                raise TypeError("Each conversation message must be a Message or dict.")
            expected = "user" if index % 2 == 0 else "assistant"
            if msg.role != expected:
                raise ValueError("History must alternate user and assistant turns.")
            if not isinstance(msg.content, str):
                raise TypeError("Message content must be a string.")
            if msg.role == "user" and not msg.content.strip():
                raise ValueError("User messages cannot be empty.")
            validated.append(msg)
        return validated

    def get_state(self) -> OllamaModelState:
        return OllamaModelState(
            version=self.version, model_name=self._model_name,
            system_instructions=self._system_instructions,
            messages=list(self._history),
        )

    def set_state(self, state):
        # Accept the original JSON representation as well as the new dataclass.
        if isinstance(state, dict):
            required = {"model_name", "system_instructions", "messages"}
            if not required.issubset(state) or set(state) - required - {"version"}:
                raise ValueError("Invalid conversation state fields.")
            state = OllamaModelState(**state)
        if not isinstance(state, OllamaModelState):
            raise TypeError("Conversation state must be an OllamaModelState or dict.")
        if type(state.version) is not int or state.version != self.version:
            raise ValueError("Unsupported conversation state version.")
        if state.model_name != self._model_name:
            raise ValueError("Saved conversation belongs to a different model.")
        if not isinstance(state.system_instructions, str):
            raise TypeError("System instructions must be a string.")
        history = self._validate_history(state.messages)
        self._history = history
        self._system_instructions = state.system_instructions

    def build_payload(self, prompt: str):
        messages = [asdict(msg) for msg in self._history]
        if self._system_instructions:
            messages.insert(0, {"role": "system", "content": self._system_instructions})
        messages.append({"role": "user", "content": prompt})
        return messages
