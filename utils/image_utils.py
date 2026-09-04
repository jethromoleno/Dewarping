"""Image loading, scaling, encoding, and point-ordering helpers."""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Generator

import cv2
import numpy as np


def load_image_bytes(file_bytes: bytes) -> np.ndarray:
    """Load image bytes into a BGR numpy array, preserving original resolution."""
    arr = np.frombuffer(file_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode uploaded image.")
    return image


def create_working_copy(
    image: np.ndarray,
    max_dim: int = 1500,
) -> tuple[np.ndarray, float]:
    """
    Create a uniformly scaled copy for fast processing.

    Returns the working copy and scale_factor (working / original).
    """
    height, width = image.shape[:2]
    longest = max(height, width)
    if longest <= max_dim:
        return image.copy(), 1.0

    scale_factor = max_dim / float(longest)
    new_width = int(round(width * scale_factor))
    new_height = int(round(height * scale_factor))
    working = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
    return working, scale_factor


def scale_points(points: np.ndarray, scale_factor: float) -> np.ndarray:
    """Map points from working-copy coordinates to full-resolution coordinates."""
    if scale_factor == 1.0:
        return points.astype(np.float32).copy()
    return (points.astype(np.float32) / scale_factor).astype(np.float32)


def scale_corners_to_full(corners: np.ndarray, scale: float) -> np.ndarray:
    """Map canvas display corners to full-resolution coordinates."""
    if scale == 1.0:
        return corners.astype(np.float32).copy()
    return (corners.astype(np.float32) / scale).astype(np.float32)


def order_points(pts: np.ndarray) -> np.ndarray:
    """
    Order four points consistently as:
    top-left, top-right, bottom-right, bottom-left.
    """
    rect = np.zeros((4, 2), dtype=np.float32)
    pts = np.array(pts, dtype=np.float32).reshape(4, 2)

    # Top-left has smallest sum; bottom-right has largest sum.
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    # Top-right has smallest diff; bottom-left has largest diff.
    diff = np.diff(pts, axis=1).reshape(-1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def order_points_cyclic(pts: np.ndarray) -> np.ndarray:
    """
    Order four points into a consistent counter-clockwise cyclic order.

    Unlike :func:`order_points`, this does NOT assume the points are roughly
    axis-aligned.  It sorts by angle around the centroid so consecutive points
    are always polygon-adjacent sides, which is rotation-invariant.  The
    returned order is [TL, TR, BR, BL] only in the sense that consecutive
    points are sides; true up/down/left/right is resolved later by
    text-orientation correction.
    """
    pts = np.array(pts, dtype=np.float32).reshape(4, 2)
    centroid = pts.mean(axis=0)
    angles = np.arctan2(pts[:, 1] - centroid[1], pts[:, 0] - centroid[0])
    ordered = pts[np.argsort(angles)].astype(np.float32)

    contour = ordered.reshape(-1, 1, 2)
    if cv2.contourArea(contour) < 0:
        ordered = ordered[::-1]
    return ordered



def encode_image_png(image: np.ndarray) -> bytes:
    """Encode a BGR image as PNG bytes for download."""
    success, buffer = cv2.imencode(".png", image)
    if not success:
        raise ValueError("Failed to encode image as PNG.")
    return buffer.tobytes()


def bgr_to_rgb(image: np.ndarray) -> np.ndarray:
    """Convert BGR OpenCV image to RGB for display."""
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def draw_corners_overlay(
    image: np.ndarray,
    corners: np.ndarray,
    labels: list[str] | None = None,
) -> np.ndarray:
    """Draw detected/selected corner points on a copy of the image."""
    overlay = image.copy()
    default_labels = ["TL", "TR", "BR", "BL"]
    labels = labels or default_labels

    pts = np.array(corners, dtype=np.float32).reshape(-1, 2)
    for idx, (x, y) in enumerate(pts):
        pt = (int(round(x)), int(round(y)))
        cv2.circle(overlay, pt, 8, (0, 255, 0), -1)
        cv2.putText(
            overlay,
            labels[idx] if idx < len(labels) else str(idx + 1),
            (pt[0] + 10, pt[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )
    return overlay


@contextmanager
def timer() -> Generator[list[float], None, None]:
    """Simple elapsed-time helper; yields a one-element list updated on exit."""
    elapsed: list[float] = [0.0]
    start = time.perf_counter()
    try:
        yield elapsed
    finally:
        elapsed[0] = (time.perf_counter() - start) * 1000.0
