"""Perspective rectification via homography."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from utils.image_utils import timer


def compute_target_size(ordered_corners: np.ndarray) -> tuple[int, int]:
    """
    Estimate output width/height from the strictly ordered TL, TR, BR, BL
    corner geometry, using the max of the two horizontal and two vertical
    edge-length pairs.

        width  = max(|BR - BL|, |TR - TL|)
        height = max(|TR - BR|, |TL - BL|)

    NOTE: ``ordered_corners`` MUST already be in [TL, TR, BR, BL] order for the
    mapping above to be correct.
    """
    tl, tr, br, bl = ordered_corners
    width_top = float(np.linalg.norm(tr - tl))
    width_bottom = float(np.linalg.norm(br - bl))
    height_right = float(np.linalg.norm(tr - br))
    height_left = float(np.linalg.norm(tl - bl))

    width = int(max(width_top, width_bottom))
    height = int(max(height_left, height_right))
    return max(width, 1), max(height, 1)


def order_corners_strict(corners: np.ndarray) -> np.ndarray:
    """Strictly order four points as [Top-Left, Top-Right, Bottom-Right, Bottom-Left].

    Uses the standard sum/diff heuristic robust to rotations up to ~90 deg:
      - TL has the smallest sum  (x + y)
      - BR has the largest sum   (x + y)
      - TR has the smallest diff (y - x), BL has the largest diff (y - x)
    """
    pts = np.array(corners, dtype=np.float32).reshape(4, 2)

    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).reshape(-1)

    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]

    return np.array([tl, tr, br, bl], dtype=np.float32)


def order_points_counter_clockwise(corners: np.ndarray) -> np.ndarray:
    """Order four points as [Top-Left, Top-Right, Bottom-Right, Bottom-Left]
    using geometric centroid-angle sorting.

    This is robust for 3D box perspectives where the classic ``x + y`` sum/diff
    heuristic can swap corners (e.g. TL<->BL or TR<->BR) because it does not
    assume the quad is roughly axis-aligned:

      1. Find the centroid of the four points.
      2. Sort points by angle around the centroid (``arctan2(y-cy, x-cx)``),
         giving a strictly counter-clockwise cyclic order.
      3. Rotate the array so the point with the smallest (x-cx)+(y-cy) --- the
         geometric Top-Left --- comes first, yielding [TL, TR, BR, BL].
    """
    pts = np.array(corners, dtype=np.float32).reshape(4, 2)
    centroid = pts.mean(axis=0)

    angles = np.arctan2(pts[:, 1] - centroid[1], pts[:, 0] - centroid[0])
    pts_sorted = pts[np.argsort(angles)]

    # Geometric Top-Left: smallest (x-cx) + (y-cy) after cyclic ordering.
    relative_sum = (pts_sorted - centroid).sum(axis=1)
    tl_idx = int(np.argmin(relative_sum))
    rect = np.roll(pts_sorted, -tl_idx, axis=0)

    return np.array(rect, dtype=np.float32)


def rectify_perspective(
    full_bgr: np.ndarray,
    corners: np.ndarray,
    border_value: tuple[int, int, int] = (255, 255, 255),
    preordered: bool = False,
) -> tuple[np.ndarray, dict[str, Any]]:
    """
    Apply perspective correction using four source corners.

    Corners must be in full-resolution image coordinates.  Unless
    ``preordered`` is True (in which case the corners are already TL, TR, BR,
    BL), the corners are first ordered as [Top-Left, Top-Right, Bottom-Right,
    Bottom-Left] using the geometric centroid-angle sort (robust to 3D box
    perspectives).
    """
    ordered = corners if preordered else order_points_counter_clockwise(corners)
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
            flags=cv2.INTER_CUBIC,
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
