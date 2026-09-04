"""In-memory image session store for the API."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import numpy as np


@dataclass
class ImageSession:
    image_id: str
    original_bgr: np.ndarray
    corrected_bgr: np.ndarray | None = None
    label_corrected_images: list[np.ndarray] | None = None
    corners: np.ndarray | None = None
    suggested_corners: np.ndarray | None = None
    processing_info: dict | None = None
    manual_corners: np.ndarray | None = None


_sessions: dict[str, ImageSession] = {}


def create_session(image_bgr: np.ndarray) -> ImageSession:
    image_id = uuid.uuid4().hex[:12]
    session = ImageSession(image_id=image_id, original_bgr=image_bgr)
    _sessions[image_id] = session
    return session


def get_session(image_id: str) -> ImageSession | None:
    return _sessions.get(image_id)
