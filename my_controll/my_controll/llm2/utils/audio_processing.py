import numpy as np


def flatten_chunk(chunk:np.ndarray)->np.ndarray:
    """Convert one audio chunk into mono-channel samples."""
    audio = np.asarray(chunk, dtype=np.float32)
    if audio.ndim not in (1, 2):
        raise ValueError(
            "Audio chunks must have shape (frames,) or (frames, channels)."
        )
    if audio.ndim > 1:
        if audio.shape[1] == 0:
            return np.empty(0, dtype=np.float32)
        audio = np.mean(audio, axis=1)
    if not np.all(np.isfinite(audio)):
        raise ValueError("Audio chunks must contain finite samples.")
    return audio.reshape(-1)

def check_for_speech(chunk:np.ndarray, activation_threshold:float)->bool:
    """Return whether a chunk looks like speech based on audio intensity."""
    if chunk.size == 0:
        return False
    rms = float(np.sqrt(np.mean(np.square(chunk, dtype=np.float64))))
    return rms >= activation_threshold

def noise_reduction(audio:np.ndarray, cutoff_frequency:float)->np.ndarray:
    """Removes frequencies below the cutoff threshold."""
    if audio.size == 0:
        return audio
    spectrum = np.fft.rfft(audio)
    frequencies = np.fft.rfftfreq(audio.size)
    spectrum[frequencies < cutoff_frequency] = 0
    return np.fft.irfft(spectrum, n=audio.size)