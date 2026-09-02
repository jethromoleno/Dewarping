"""
Experimental nonlinear geometric correction.

This module is intentionally separate from perspective (homography) correction.
It applies a mild barrel-style undistortion as a placeholder that can later be
replaced with thin-plate spline registration or learned dewarping.
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def apply_nonlinear_correction(
    image: np.ndarray,
    enabled: bool = False,
    k1: float = -0.08,
    k2: float = 0.01,
) -> tuple[np.ndarray, dict[str, Any]]:
    """
    Optionally apply mild nonlinear correction after perspective rectification.

    Uses a conservative radial undistortion model. This cannot perfectly reverse
    arbitrary unknown warping without additional information.
    """
    info: dict[str, Any] = {
        "applied": False,
        "method": "radial_undistort",
        "note": "Experimental post-homography correction only.",
    }

    if not enabled:
        return image, info

    height, width = image.shape[:2]
    focal = max(width, height)
    camera_matrix = np.array(
        [[focal, 0, width / 2.0], [0, focal, height / 2.0], [0, 0, 1]],
        dtype=np.float64,
    )
    dist_coeffs = np.array([k1, k2, 0, 0, 0], dtype=np.float64)

    corrected = cv2.undistort(image, camera_matrix, dist_coeffs)
    info.update({"applied": True, "k1": k1, "k2": k2})
    return corrected, info
