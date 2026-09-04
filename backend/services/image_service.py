"""Image loading and encoding helpers."""

from __future__ import annotations

import numpy as np

from utils.image_utils import load_image_bytes as _load_image_bytes


def load_uploaded_image(file_bytes: bytes) -> np.ndarray:
    return _load_image_bytes(file_bytes)
