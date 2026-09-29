from typing import Any, Mapping, Optional, Sequence
import unicodedata
import re


def unwrap_model_response(response:Any)->str:
    # Extract message
    if isinstance(response, Mapping):
        msg = response.get("message")
    else:
        msg = getattr(response, "message", None)
    # Extract content from message
    if isinstance(msg, Mapping):
        content = msg.get("content")
    else:
        content = getattr(msg, "content", None)
    # Validate content
    if not isinstance(content, str):
        raise RuntimeError(
            "Invalid response type from model "
            f"(expected str, got {type(content)})."
        )
    return content

def trim_unfinished_sentence(response:str)->str:
    """Remove a trailing fragment, retaining text if no sentence is complete."""
    ends = list(re.finditer(r'[.!?](?:["\u201d\u2019\x27)]*)(?=\s|$)', response))
    out = response[:ends[-1].end()].strip() if ends else response.strip()
    return out

def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = text.replace("’", "'").replace("'", "")
    return " ".join(re.findall(r"\w+", text))

def prepare_keywords(stop_kwrds: Optional[Sequence[str]]) -> list[str]:
    if stop_kwrds is None:
        return []
    if isinstance(stop_kwrds, (str, bytes)) or not isinstance(stop_kwrds, Sequence):
        raise TypeError("Stop keywords must be a sequence of strings.")
    normalized = []
    for keyword in stop_kwrds:
        if not isinstance(keyword, str):
            raise TypeError("Every stop keyword must be a string.")
        keyword = normalize_text(keyword)
        if not keyword:
            raise ValueError("Stop keywords must contain words.")
        normalized.append(" " + keyword + " ")
    return normalized

def merge_transcript(previous: str, segment: str) -> str:
    if not previous:
        return segment
    before, after = previous.split(), segment.split()
    for size in range(min(len(before), len(after)), 0, -1):
        if (normalize_text(" ".join(before[-size:]))
                == normalize_text(" ".join(after[:size]))):
            after = after[size:]
            break
    return " ".join(before + after)
