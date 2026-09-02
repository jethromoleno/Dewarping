"""Perspective rectification via homography."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from utils.image_utils import order_points, timer


def compute_target_size(ordered_corners: np.ndarray) -> tuple[int, int]:
    """
    Estimate output width/height from the ordered corner geometry.

    Width  = max distance between top and bottom edge lengths.
    Height = max distance between left and right edge lengths.
    """
    tl, tr, br, bl = ordered_corners
    width_top = float(np.linalg.norm(tr - tl))
    width_bottom = float(np.linalg.norm(br - bl))
    height_left = float(np.linalg.norm(bl - tl))
    height_right = float(np.linalg.norm(br - tr))

    width = int(max(width_top, width_bottom))
    height = int(max(height_left, height_right))
    return max(width, 1), max(height, 1)


def rectify_perspective(
    full_bgr: np.ndarray,
    corners: np.ndarray,
    border_value: tuple[int, int, int] = (255, 255, 255),
) -> tuple[np.ndarray, dict[str, Any]]:
    """
    Apply perspective correction using four source corners.

    Corners must be in full-resolution image coordinates.
    """
    ordered = order_points(corners)
    width, height = compute_target_size(ordered)

    dst = np.array(
        [
            [0, 0],
            [width - 1, 0],
            [width - 1, height - 1],
            [0, height - 1],
        ],
        dtype=np.float32,
    )

    with timer() as elapsed:
        matrix = cv2.getPerspectiveTransform(ordered, dst)
        corrected = cv2.warpPerspective(
            full_bgr,
            matrix,
            (width, height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=border_value,
        )

    info: dict[str, Any] = {
        "source_corners": ordered.tolist(),
        "output_size": (width, height),
        "homography_matrix": matrix.tolist(),
        "perspective_time_ms": elapsed[0],
        "input_size": (full_bgr.shape[1], full_bgr.shape[0]),
    }
    return corrected, info
