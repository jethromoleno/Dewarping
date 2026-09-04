"""Business logic services for image correction pipeline."""

from __future__ import annotations

import time

import cv2
import numpy as np

from backend.session_store import ImageSession
from processing.nonlinear import apply_nonlinear_correction
from processing.perspective import rectify_perspective
from utils.image_utils import (
    create_working_copy,
    draw_corners_overlay,
    encode_image_png,
    order_points,
    scale_points,
)


def run_correction(
    session: ImageSession,
    corners: np.ndarray,
    enable_nonlinear: bool,
    detection_info: dict | None = None,
) -> None:
    total_start = time.perf_counter()

    corrected, perspective_info = rectify_perspective(session.original_bgr, corners)
    corrected, nonlinear_info = apply_nonlinear_correction(
        corrected,
        enabled=enable_nonlinear,
    )

    total_ms = (time.perf_counter() - total_start) * 1000.0
    session.corrected_bgr = corrected
    session.corners = corners
    session.processing_info = {
        "detection": detection_info or {},
        "perspective": perspective_info,
        "nonlinear": nonlinear_info,
        "total_time_ms": total_ms,
    }


def run_automatic_correction(
    session: ImageSession,
    enable_nonlinear: bool,
) -> bool:
    working, scale_factor = create_working_copy(session.original_bgr)

    from processing.detection import detect_document_quad

    detection = detect_document_quad(working)

    if detection.corners is not None and detection.success:
        full_corners = scale_points(detection.corners, scale_factor)
        session.suggested_corners = full_corners

        run_correction(
            session=session,
            corners=full_corners,
            enable_nonlinear=enable_nonlinear,
            detection_info={
                "mode": "automatic",
                "score": detection.score,
                "reason": detection.reason,
                "working_scale_factor": scale_factor,
                "debug": detection.debug,
            },
        )
        return True

    return False
