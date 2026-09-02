"""Preprocessing steps for boundary detection."""

from __future__ import annotations

import cv2
import numpy as np


def preprocess_for_detection(working_bgr: np.ndarray) -> np.ndarray:
    """
    Prepare a grayscale image for edge/contour detection.

    Steps:
    1. Convert to grayscale
    2. Light bilateral denoising (preserves edges)
    3. CLAHE contrast enhancement
    4. Mild Gaussian blur to reduce noise before Canny
    """
    gray = cv2.cvtColor(working_bgr, cv2.COLOR_BGR2GRAY)
    denoised = cv2.bilateralFilter(gray, d=5, sigmaColor=50, sigmaSpace=50)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)
    return blurred
