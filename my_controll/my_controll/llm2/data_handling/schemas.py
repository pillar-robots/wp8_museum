from dataclasses import dataclass, field
from typing import Dict, List, Literal


@dataclass(frozen=True)
class TranscriptResult:
    """
    Result returned by the speech transcription pipeline.

    Parameters
    ---
    text : str (default = '')
        Transcribed text.
    metadata : dict (default = {})
        Additional info about transcription.
    """
    text:str = ""
    metadata:Dict = field(default_factory=dict)


@dataclass(frozen=True)
class Message:
    role: Literal["system", "user", "assistant"]
    content: str

@dataclass(frozen=True)
class OllamaModelState:
    model_name:str
    system_instructions:str
    messages:List[Message]
    version:int = 1