import os
import re


def _clean_model_id(model_id: str) -> str:
    """
    Return a filesystem-safe model identifier.
    
    Parameters
    ---
    model_id : str
        The id to clean.

    Returns
    ---
    str
        The safe id.
    """
    if not isinstance(model_id, str):
        raise TypeError("Model id must be a string.")
    if not model_id.strip():
        raise ValueError("Model id must be a non-empty string.")
    new_name = re.sub(r"[^A-Za-z0-9._-]+", "-", model_id.strip())
    new_name = re.sub(r"-+", "-", new_name).strip("-._")
    return new_name or "model"


def make_model_dir(model_id: str, path: str | os.PathLike[str]) -> str:
    """
    Create the model storage directory. It will be saved at 'path/model_id'.
    `model_id` will be sanitized to remove any problematic characters.

    Parameters
    ---
    model_id : str
        The model id. It's appended at the end of the path.
    path : str or os.PathLike[str]
        The target directory where the folder will be created.

    Returns
    ---
    str
        Path to model directory.
    """
    model_dir = _clean_model_id(model_id)
    root_path = os.fspath(path)
    if not isinstance(root_path, str) or not root_path.strip():
        raise ValueError("Model storage path must be a non-empty text path.")
    # Joining path components also supports Path objects and platform separators.
    full_path = os.path.join(root_path, model_dir)
    os.makedirs(full_path, exist_ok=True)
    return full_path
