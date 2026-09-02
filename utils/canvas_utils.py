"""Fabric.js canvas object helpers for manual bounding-box editing."""

from __future__ import annotations

from typing import Any

import numpy as np

from utils.image_utils import order_points, scale_corners_to_full


def display_corners_to_full(
    corners_display: list[list[float]] | np.ndarray,
    display_scale: float,
) -> np.ndarray:
    """Convert display-space corners to full-resolution ordered corners."""
    points = np.array(corners_display, dtype=np.float32).reshape(-1, 2)
    return order_points(scale_corners_to_full(points, display_scale))


def json_has_quad_polygon(canvas_json: dict[str, Any] | None) -> bool:
    """Return True when canvas JSON contains a quadrilateral polygon."""
    if not canvas_json or "objects" not in canvas_json:
        return False
    for obj in canvas_json["objects"]:
        if obj.get("type") == "polygon" and len(obj.get("points", [])) == 4:
            return True
    return False
