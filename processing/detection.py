"""Automatic quadrilateral boundary detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from processing.preprocessing import preprocess_for_detection
from utils.image_utils import order_points


@dataclass
class DetectionResult:
    """Structured output from automatic boundary detection."""

    success: bool
    corners: np.ndarray | None = None
    score: float = 0.0
    reason: str = ""
    debug: dict[str, Any] = field(default_factory=dict)


def _angle_between(v1: np.ndarray, v2: np.ndarray) -> float:
    """Return angle in degrees between two 2D vectors."""
    denom = np.linalg.norm(v1) * np.linalg.norm(v2)
    if denom < 1e-6:
        return 0.0
    cos_angle = np.clip(np.dot(v1, v2) / denom, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))


def _interior_angles(ordered: np.ndarray) -> list[float]:
    """Compute interior angles of an ordered quadrilateral."""
    angles: list[float] = []
    for i in range(4):
        p_prev = ordered[(i - 1) % 4]
        p_curr = ordered[i]
        p_next = ordered[(i + 1) % 4]
        v1 = p_prev - p_curr
        v2 = p_next - p_curr
        angles.append(_angle_between(v1, v2))
    return angles


def _side_lengths(ordered: np.ndarray) -> list[float]:
    """Return side lengths TL-TR, TR-BR, BR-BL, BL-TL."""
    return [
        float(np.linalg.norm(ordered[1] - ordered[0])),
        float(np.linalg.norm(ordered[2] - ordered[1])),
        float(np.linalg.norm(ordered[3] - ordered[2])),
        float(np.linalg.norm(ordered[0] - ordered[3])),
    ]


def _border_hits(ordered: np.ndarray, shape: tuple[int, ...]) -> int:
    """Count corners near the image border."""
    height, width = shape[:2]
    margin = min(width, height) * 0.02
    hits = 0
    for x, y in ordered:
        if x <= margin or y <= margin or x >= width - margin or y >= height - margin:
            hits += 1
    return hits


def is_valid_quadrilateral(
    pts: np.ndarray,
    image_shape: tuple[int, ...],
) -> tuple[bool, str]:
    """
    Validate that a quadrilateral is geometrically reasonable for rectification.
    """
    height, width = image_shape[:2]
    image_area = float(height * width)
    ordered = order_points(pts)
    contour = ordered.reshape(-1, 1, 2).astype(np.float32)

    area = float(cv2.contourArea(contour))
    if area < 0.05 * image_area:
        return False, "Area too small"

    # Reject quads that are essentially the image frame.
    border_hits = _border_hits(ordered, image_shape)
    if area > 0.90 * image_area and border_hits >= 3:
        return False, "Matches image frame"

    if not cv2.isContourConvex(contour.astype(np.int32)):
        return False, "Not convex"

    for x, y in ordered:
        if x < 0 or y < 0 or x >= width or y >= height:
            return False, "Corner outside image bounds"

    angles = _interior_angles(ordered)
    for angle in angles:
        if angle < 45.0 or angle > 135.0:
            return False, f"Angle out of range: {angle:.1f}°"

    sides = _side_lengths(ordered)
    width_avg = (sides[0] + sides[2]) / 2.0
    height_avg = (sides[1] + sides[3]) / 2.0
    if width_avg < 1.0 or height_avg < 1.0:
        return False, "Degenerate side lengths"

    aspect = max(width_avg, height_avg) / max(min(width_avg, height_avg), 1.0)
    if aspect > 10.0:
        return False, f"Extreme aspect ratio: {aspect:.2f}"

    return True, "OK"


def _border_proximity_penalty(ordered: np.ndarray, shape: tuple[int, ...]) -> float:
    """Penalize quads that hug the image border."""
    return _border_hits(ordered, shape) / 4.0


def _score_quadrilateral(ordered: np.ndarray, shape: tuple[int, ...]) -> float:
    """Score a candidate quadrilateral; higher is better."""
    height, width = shape[:2]
    image_area = float(height * width)
    contour = ordered.reshape(-1, 1, 2).astype(np.float32)
    area = float(cv2.contourArea(contour))
    area_score = min(area / image_area, 0.90)

    angles = _interior_angles(ordered)
    angle_dev = sum(abs(a - 90.0) for a in angles) / 4.0
    angle_score = max(0.0, 1.0 - angle_dev / 45.0)

    sides = _side_lengths(ordered)
    horiz_ratio = min(sides[0], sides[2]) / max(sides[0], sides[2], 1.0)
    vert_ratio = min(sides[1], sides[3]) / max(sides[1], sides[3], 1.0)
    side_score = (horiz_ratio + vert_ratio) / 2.0

    border_penalty = _border_proximity_penalty(ordered, shape)

    score = (
        0.40 * area_score
        + 0.30 * angle_score
        + 0.20 * side_score
        + 0.10 * (1.0 - border_penalty)
    )
    return float(score)


def _canny_edges(gray: np.ndarray) -> np.ndarray:
    """Adaptive Canny thresholds based on image median intensity."""
    median = float(np.median(gray))
    lower = int(max(0, 0.66 * median))
    upper = int(min(255, 1.33 * median))
    if upper <= lower:
        upper = lower + 1
    return cv2.Canny(gray, lower, upper)


def _build_edge_maps(gray: np.ndarray) -> list[np.ndarray]:
    """Build multiple edge/binary maps to improve contour discovery."""
    maps: list[np.ndarray] = []

    canny = _canny_edges(gray)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    maps.append(cv2.morphologyEx(cv2.dilate(canny, kernel, iterations=1), cv2.MORPH_CLOSE, kernel, iterations=2))

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    adaptive = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2,
    )
    maps.append(cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel, iterations=3))

    _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    maps.append(cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel, iterations=2))

    return maps


def _approximate_quad(contour: np.ndarray) -> np.ndarray | None:
    """
    Try to reduce a contour to four corners using multiple epsilon values
    and convex-hull / min-area-rectangle fallbacks.
    """
    hull = cv2.convexHull(contour)
    peri = cv2.arcLength(hull, True)

    for eps_factor in (0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.06, 0.08):
        approx = cv2.approxPolyDP(hull, eps_factor * peri, True)
        if len(approx) == 4:
            return approx.reshape(4, 2).astype(np.float32)

    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    return box.astype(np.float32)


def _collect_contours(edge_maps: list[np.ndarray]) -> list[np.ndarray]:
    """Gather contours from multiple edge maps."""
    all_contours: list[np.ndarray] = []
    for edge_map in edge_maps:
        contours, _ = cv2.findContours(edge_map, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        all_contours.extend(contours)
    return all_contours


def _bright_region_contours(gray: np.ndarray) -> list[np.ndarray]:
    """Find contours of large bright regions (typical white documents)."""
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, bright = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    bright = cv2.morphologyEx(bright, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours


def detect_document_quad(working_bgr: np.ndarray) -> DetectionResult:
    """
    Detect the largest plausible document quadrilateral in a working-copy image.

    Returns a DetectionResult; never raises on detection failure.
    """
    debug: dict[str, Any] = {
        "contour_count": 0,
        "candidates": 0,
        "rejected": [],
    }

    gray = preprocess_for_detection(working_bgr)
    edge_maps = _build_edge_maps(gray)
    contours = _collect_contours(edge_maps)
    contours.extend(_bright_region_contours(gray))
    debug["contour_count"] = len(contours)

    height, width = working_bgr.shape[:2]
    image_area = float(height * width)
    min_area = 0.05 * image_area

    best_corners: np.ndarray | None = None
    best_score = 0.0
    seen: set[tuple[int, ...]] = set()

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        quad = _approximate_quad(contour)
        if quad is None:
            continue

        ordered = order_points(quad)
        key = tuple(int(round(v)) for pt in ordered for v in pt)
        if key in seen:
            continue
        seen.add(key)

        debug["candidates"] += 1
        valid, reason = is_valid_quadrilateral(ordered, working_bgr.shape)
        if not valid:
            debug["rejected"].append(reason)
            continue

        score = _score_quadrilateral(ordered, working_bgr.shape)
        if score > best_score:
            best_score = score
            best_corners = ordered

    min_acceptable_score = 0.35
    if best_corners is None or best_score < min_acceptable_score:
        return DetectionResult(
            success=False,
            reason="No reliable quadrilateral detected",
            debug=debug,
        )

    return DetectionResult(
        success=True,
        corners=best_corners,
        score=best_score,
        reason="Quadrilateral detected",
        debug=debug,
    )
