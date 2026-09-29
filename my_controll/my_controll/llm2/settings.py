from __future__ import annotations

from pathlib import Path

if __package__:
    from .audio_transcription import (
        AudioSourceDeviceConfig, TranscriptorConfig, SpeechTranscriptionPipelineConfig,
    )
    from .inference import OllamaModelConfig
    from .inference.system_instructions import SYSTEM_INSTRUCTIONS, PUBLIC_INITIAL_PROMPT
else:
    from audio_transcription import (
        AudioSourceDeviceConfig, TranscriptorConfig, SpeechTranscriptionPipelineConfig,
    )
    from inference import OllamaModelConfig
    from inference.system_instructions import SYSTEM_INSTRUCTIONS, PUBLIC_INITIAL_PROMPT


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def local_whisper_directory() -> Path:
    # Check expected path
    model_dir = PROJECT_ROOT / "models" / "large-v3-turbo"
    # Look for model.bin as it's what the loader reads
    if (model_dir / "model.bin").is_file():
        return model_dir
    # If unsuccessful, check for snapshots
    cache_dir = model_dir / "models--Systran--faster-whisper-small"
    revision_file = cache_dir / "refs" / "main"
    if revision_file.is_file():
        revision = revision_file.read_text(encoding="utf-8").strip()
        # Cache revisions are single directory names
        if revision and all(
            character in "0123456789abcdef" for character in revision
        ):
            snapshot = cache_dir / "snapshots" / revision
            if (snapshot / "model.bin").is_file():
                return snapshot
    return model_dir


# ============ CONFIG CLASSES ============

AUDIO_SOURCE_CONFIG = AudioSourceDeviceConfig(chunk_duration=0.25, max_buffer_size=20)
TRANSCRIPTOR_CONFIG = TranscriptorConfig(
    storage_dir="/home/citic_lab/my_controll_migration_ws/src/my_controll/my_controll/llm2/models/large-v3-turbo",
    device="cpu",
    dtype="int8",  # Quantization works fine
    language="en",
    beam_size=1,
)
TRANSCRIPTION_PIPELINE_CONFIG = SpeechTranscriptionPipelineConfig(
    audio_source_device_config=AUDIO_SOURCE_CONFIG,
    transcriptor_config=TRANSCRIPTOR_CONFIG,
    # 0.01 is low enough for common microphone noise to look like continuous
    # speech, preventing end-of-utterance detection.
    activation_threshold=0.02,
    cutoff_frequency=0.01,
    silence_patience=3,
    min_audio_seconds=0.5,
    # Bound forced transcription to ten seconds instead of thirty.
    max_buffer_size=40,
    overlap_on_full_buffer=2,
)
# Dream-v0 needs a diffusion sampler but the Ollama endpoint decodes autoregressively
# WeDLM is diffusion-trained but supports regular causal attention
# This uses WeDLM's causal path, not its faster native parallel decoder
# Also the dedicated wedlm engine could be used for more optimization
MODEL_CONFIG = OllamaModelConfig(
    model_name="llama3.1:8b",
    # model_name="llama3.2:1b",
    system_instructions=SYSTEM_INSTRUCTIONS,
    options={
        # Allow space for the system knowledge base and resumed dialogue
        "num_ctx": 4096,
        "num_predict": 96,
        "temperature": 0.3,
        "top_p": 0.95,
        "repeat_penalty": 1.0,
        # The GGUF embeds a ChatML template but its generated Ollama manifest
        # omits the matching stop token
        "stop": ["<|im_end|>"],
    }
)


# ========= OTHER CONFIG VARS =========


IDLE_SLEEP_SECONDS = 0.01

STOP_KEYWORDS = (
    "goodbye",
    "bye",
    "let's continue the exhibition",
    "i'll take it from here",
    "good job thiago",
)
PUBLIC_SLEEP_SECONDS_TO_SHUTDOWN = 20
ESTIMATED_WORD_UTTERANCE_TIME_SECONDS = 0.4

STATE_PATH = "/home/citic_lab/my_controll_migration_ws/src/my_controll/my_controll/llm2/state/state.json"
SPEECH_LIMIT = 5