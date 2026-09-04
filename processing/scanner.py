"""CamScanner-grade label extraction: perspective rectification, residual
deskew, and scan-quality enhancement.

Pipeline (per detected label quad):
  1. ``rectify_perspective``  - flatten the quad onto a rectangular grid via
     4-point homography (getPerspectiveTransform / warpPerspective).
  2. ``fine_deskew``          - remove residual sub-degree tilt so text
     baselines / barcode rows are exactly horizontal.
  3. ``enhance_scan``         - unsharp-mask sharpen + mild contrast so the
     crop looks like a clean document-scan rather than a live camera crop.
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from processing.orientation import correct_orientation
from processing.perspective import order_points_counter_clockwise, rectify_perspective
from utils.image_utils import timer


def _estimate_text_angle(image_bgr: np.ndarray) -> float:
    """Estimate residual skew (deg) of text/barcode lines in an upright crop.

    Uses a projection-profile sweep: for a small range of rotation angles we
    measure how "line-banded" the horizontal ink profile is.  The angle that
    maximizes banding is the skew correction.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(gray, 40, 120)

    h, w = gray.shape[:2]
    if min(w, h) < 32 or not np.any(edges):
        return 0.0

    angles = np.arange(-8.0, 8.0, 0.5)
    best_angle = 0.0
    best_score = -1.0
    center = (w / 2.0, h / 2.0)

    for deg in angles:
        matrix = cv2.getRotationMatrix2D(center, -deg, 1.0)
        rot_edges = cv2.warpAffine(
            edges, matrix, (w, h),
            flags=cv2.INTER_NEAREST,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )
        row_profile = rot_edges.sum(axis=1).astype(np.float64)
        std = float(np.std(row_profile))
        if std > best_score:
            best_score = std
            best_angle = deg

    if best_angle > -0.2 and best_angle < 0.2:
        return 0.0
    return float(best_angle)


def _rotate_by(image_bgr: np.ndarray, angle: float) -> np.ndarray:
    h, w = image_bgr.shape[:2]
    center = (w / 2.0, h / 2.0)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image_bgr, matrix, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )
    return rotated


def fine_deskew(image_bgr: np.ndarray, min_angle: float = 0.3) -> np.ndarray:
    """Remove small residual tilt by rotating to exactly horizontal text."""
    angle = _estimate_text_angle(image_bgr)
    if abs(angle) < min_angle:
        return image_bgr.copy()
    return _rotate_by(image_bgr, -angle)


def enhance_scan(image_bgr: np.ndarray) -> np.ndarray:
    """Sharpen and lightly normalize a rectified crop for a crisp scan look."""
    result = image_bgr.copy()

    blur = cv2.GaussianBlur(result, (0, 0), 1.2)
    result = cv2.addWeighted(result, 1.4, blur, -0.4, 0)

    if result.ndim == 3:
        clahe = cv2.createCLAHE(clipLimit=1.6, tileGridSize=(8, 8))
        lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
        result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    return result


def extract_label_scanned(
    original_bgr: np.ndarray,
    corners: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Rectify, auto-orient, fine-deskew and enhance one label crop.

    Returns ``(scanned_bgr, info)``.
    """
    info: dict[str, Any] = {}

    with timer() as t_total:
        with timer() as t_warp:
            # Geometric centroid-angle corner ordering (robust to 3D box
            # perspectives) and homography dewarp (INTER_CUBIC, exact
            # width/height formula).
            ordered = order_points_counter_clockwise(corners)
            corrected, perspective_info = rectify_perspective(original_bgr, ordered, preordered=True)
            info["homography_ms"] = perspective_info.get("perspective_time_ms", 0.0)
            info["warp_size"] = perspective_info.get("output_size")

        with timer() as t_orient:
            # Strictly upright correction: rotates 0/90/180/270 so text and
            # barcode are right-side up and horizontally readable.  No forced
            # portrait/landscape re-rotation, so the true aspect is preserved
            # and the output can never be inverted or distorted by a redundant
            # intermediate rotation.
            upright = correct_orientation(corrected)
            info["orientation_ms"] = t_orient[0]

        with timer() as t_deskew:
            deskewed = fine_deskew(upright)
            info["deskew_ms"] = t_deskew[0]

        with timer() as t_enhance:
            scanned = enhance_scan(deskewed)
            info["enhance_ms"] = t_enhance[0]

    info["total_ms"] = t_total[0]
    info["final_size"] = (scanned.shape[1], scanned.shape[0])
    return scanned, info
