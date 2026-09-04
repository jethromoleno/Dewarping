"""Automatic sticker-label detection and extraction.

Pipeline:
  1. Preprocess (grayscale, contrast enhance, edge sharpen)
  2. Multi-strategy contour extraction (adaptive threshold, Canny, bright regions)
  3. Quadrilateral approximation per contour
  4. Geometric + label-specific validation
  5. Score candidates and return ALL labels above threshold
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from utils.image_utils import order_points


@dataclass
class SingleLabel:
    corners: np.ndarray
    score: float


@dataclass
class LabelDetectionResult:
    success: bool
    labels: list[SingleLabel] = field(default_factory=list)
    reason: str = ""
    debug: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def _preprocess_label(gray: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    laplacian = cv2.Laplacian(enhanced, cv2.CV_64F)
    sharp = cv2.convertScaleAbs(laplacian)
    blended = cv2.addWeighted(enhanced, 0.7, sharp, 0.3, 0)

    denoised = cv2.bilateralFilter(blended, d=7, sigmaColor=50, sigmaSpace=50)
    blurred = cv2.GaussianBlur(denoised, (3, 3), 0)
    return blurred


# ---------------------------------------------------------------------------
# Contour extraction strategies
# ---------------------------------------------------------------------------

def _extract_contours(processed: np.ndarray) -> list[np.ndarray]:
    all_contours: list[np.ndarray] = []

    adaptive = cv2.adaptiveThreshold(
        processed, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 15, 5,
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    adaptive = cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel, iterations=2)
    adaptive = cv2.dilate(adaptive, kernel, iterations=1)
    contours, _ = cv2.findContours(adaptive, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    all_contours.extend(contours)

    median = float(np.median(processed))
    lower = int(max(0, 0.5 * median))
    upper = int(min(255, 1.5 * median))
    if upper <= lower:
        upper = lower + 2
    edges = cv2.Canny(processed, lower, upper)
    edges = cv2.dilate(edges, kernel, iterations=1)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours2, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    all_contours.extend(contours2)

    blurred = cv2.GaussianBlur(processed, (5, 5), 0)
    _, bright = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bright_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    bright = cv2.morphologyEx(bright, cv2.MORPH_CLOSE, bright_kernel, iterations=2)
    contours3, _ = cv2.findContours(bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    all_contours.extend(contours3)

    return all_contours


# ---------------------------------------------------------------------------
# Quadrilateral approximation
# ---------------------------------------------------------------------------

def _approximate_quad(contour: np.ndarray) -> np.ndarray | None:
    hull = cv2.convexHull(contour)
    peri = cv2.arcLength(hull, True)
    for eps in (0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.06, 0.08):
        approx = cv2.approxPolyDP(hull, eps * peri, True)
        if len(approx) == 4:
            return approx.reshape(4, 2).astype(np.float32)
    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    return box.astype(np.float32)


# ---------------------------------------------------------------------------
# Geometric helpers
# ---------------------------------------------------------------------------

def _angle_between(v1: np.ndarray, v2: np.ndarray) -> float:
    denom = np.linalg.norm(v1) * np.linalg.norm(v2)
    if denom < 1e-6:
        return 0.0
    cos_a = np.clip(np.dot(v1, v2) / denom, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_a)))


def _interior_angles(ordered: np.ndarray) -> list[float]:
    angles: list[float] = []
    for i in range(4):
        p_prev = ordered[(i - 1) % 4]
        p_curr = ordered[i]
        p_next = ordered[(i + 1) % 4]
        angles.append(_angle_between(p_prev - p_curr, p_next - p_curr))
    return angles


def _side_lengths(ordered: np.ndarray) -> list[float]:
    return [
        float(np.linalg.norm(ordered[1] - ordered[0])),
        float(np.linalg.norm(ordered[2] - ordered[1])),
        float(np.linalg.norm(ordered[3] - ordered[2])),
        float(np.linalg.norm(ordered[0] - ordered[3])),
    ]


def _is_convex(pts: np.ndarray) -> bool:
    contour = pts.reshape(-1, 1, 2).astype(np.int32)
    return bool(cv2.isContourConvex(contour))


def _corner_count_near_border(ordered: np.ndarray, shape: tuple[int, ...]) -> int:
    height, width = shape[:2]
    margin_w = width * 0.01
    margin_h = height * 0.01
    hits = 0
    for x, y in ordered:
        if x <= margin_w or y <= margin_h or x >= width - margin_w or y >= height - margin_h:
            hits += 1
    return hits


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _quad_interior_stats(ordered: np.ndarray, gray: np.ndarray) -> tuple[float, float]:
    """Measure the brightness of the area inside a candidate quad.

    Returns ``(white_fraction, mean_luminance)``.  ``white_fraction`` is the
    share of interior pixels that are near-white (>= ``WHITE_THRESH``); a real
    sticker label is a light/white sheet against a darker box, so a candidate
    that is not predominantly white is almost certainly the box/background.
    """
    white_thresh = 200
    height, width = gray.shape[:2]

    mask = np.zeros((height, width), dtype=np.uint8)
    pts = ordered.reshape(-1, 1, 2).astype(np.int32)
    cv2.fillPoly(mask, [pts], 255)

    idx = mask > 0
    if not np.any(idx):
        return 0.0, 0.0

    interior = gray[idx].astype(np.float32)
    white_fraction = float(np.count_nonzero(interior >= white_thresh)) / float(interior.size)
    mean_luminance = float(interior.mean())
    return white_fraction, mean_luminance


def _encompasses_outer_bbox(
    ordered: np.ndarray,
    image_shape: tuple[int, ...],
) -> bool:
    """True if the candidate quad essentially covers the whole package frame.

    A real sticker label sits on only a portion of the package surface, so a
    quad that spans the full (or near-full) outer bounding region of the image
    is a cardboard-box face, not a label.  We compare the candidate's bounding
    rectangle against the image frame.
    """
    height, width = image_shape[:2]

    x_min = float(ordered[:, 0].min())
    x_max = float(ordered[:, 0].max())
    y_min = float(ordered[:, 1].min())
    y_max = float(ordered[:, 1].max())

    cover_w = (x_max - x_min) / float(width)
    cover_h = (y_max - y_min) / float(height)

    # A label should not span most of the image in BOTH axes.  Reject when
    # the quad covers >= 75% of the frame in both width and height, or >= 90%
    # of the frame area.
    if cover_w >= 0.75 and cover_h >= 0.75:
        return True
    if cover_w * cover_h >= 0.90:
        return True
    return False


def _edge_density_ratio(
    ordered: np.ndarray,
    gray: np.ndarray,
    min_threshold: float = 0.03,
) -> float:
    """Fraction of strong edges inside the candidate quad.

    A real sticker label carries dense, high-contrast content (barcodes and
    printed text blocks), producing many strong edges.  Blank cardboard or a
    featureless background patch produces very few edges.  Returns the
    interior Canny edge fraction.
    """
    height, width = gray.shape[:2]

    mask = np.zeros((height, width), dtype=np.uint8)
    pts = ordered.reshape(-1, 1, 2).astype(np.int32)
    cv2.fillPoly(mask, [pts], 255)

    idx = mask > 0
    if not np.any(idx):
        return 0.0

    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blurred, 50, 150)
    interior_edges = cv2.bitwise_and(edges, edges, mask=mask)
    return float(np.count_nonzero(interior_edges)) / float(np.count_nonzero(idx))


def _is_valid_label(
    ordered: np.ndarray,
    image_shape: tuple[int, ...],
    gray: np.ndarray | None = None,
) -> tuple[bool, str]:
    height, width = image_shape[:2]
    image_area = float(height * width)
    contour = ordered.reshape(-1, 1, 2).astype(np.float32)
    area = float(cv2.contourArea(contour))

    if area < 0.005 * image_area:
        return False, "Area too small for a label"

    if area > 0.60 * image_area:
        return False, "Area too large (likely the whole box/background)"

    # Ignore anything that encompasses the whole outer bounding box of the
    # package (e.g. a full cardboard face).
    if _encompasses_outer_bbox(ordered, image_shape):
        return False, "Quad covers the whole package/outer bounding box"

    # A sticker label is a small light patch on a (typically darker) box, so
    # reject any candidate that does not have a distinctly white interior.
    if gray is not None:
        white_frac, mean_lum = _quad_interior_stats(ordered, gray)
        if white_frac < 0.35:
            return False, f"Not a white label (white={white_frac:.2f}, mean={mean_lum:.0f})"
        if mean_lum < 120.0:
            return False, f"Label interior too dark (mean={mean_lum:.0f})"

    if not _is_convex(ordered):
        return False, "Not convex"

    border_hits = _corner_count_near_border(ordered, image_shape)
    if border_hits >= 4:
        return False, "Corners touch all borders"

    for x, y in ordered:
        if x < 0 or y < 0 or x >= width or y >= height:
            return False, "Corner outside image bounds"

    angles = _interior_angles(ordered)
    for angle in angles:
        if angle < 50.0 or angle > 130.0:
            return False, f"Angle out of range: {angle:.1f}"

    sides = _side_lengths(ordered)
    w_avg = (sides[0] + sides[2]) / 2.0
    h_avg = (sides[1] + sides[3]) / 2.0
    if w_avg < 1.0 or h_avg < 1.0:
        return False, "Degenerate side lengths"

    aspect = max(w_avg, h_avg) / max(min(w_avg, h_avg), 1.0)
    # Typical shipping/routing labels are moderate rectangles; narrow strips
    # (e.g. box tape or thin slivers) are not labels.
    if aspect > 6.0:
        return False, f"Extreme aspect ratio: {aspect:.2f}"
    if aspect < 1.05:
        return False, f"Too square to be a label: {aspect:.2f}"

    fill = area / (w_avg * h_avg) if (w_avg * h_avg) > 0 else 0.0
    if fill < 0.45:
        return False, "Low rectangularity (not a label shape)"

    # Require dense high-contrast content (barcode/text).  A purely blank
    # white patch is not a usable label.
    if gray is not None:
        edge_frac = _edge_density_ratio(ordered, gray)
        if edge_frac < 0.02:
            return False, f"No dense content (barcode/text) (edges={edge_frac:.4f})"

    return True, "OK"


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _score_label(
    ordered: np.ndarray,
    image_shape: tuple[int, ...],
    processed: np.ndarray,
    gray: np.ndarray | None = None,
) -> float:
    height, width = image_shape[:2]
    image_area = float(height * width)
    contour = ordered.reshape(-1, 1, 2).astype(np.float32)
    area = float(cv2.contourArea(contour))

    area_ratio = area / image_area
    if area_ratio < 0.02:
        area_score = area_ratio / 0.02 * 0.5
    elif area_ratio <= 0.40:
        area_score = 0.5 + 0.5 * (1.0 - abs(area_ratio - 0.15) / 0.25)
    else:
        area_score = max(0.0, 1.0 - (area_ratio - 0.40) / 0.45)

    angles = _interior_angles(ordered)
    angle_dev = sum(abs(a - 90.0) for a in angles) / 4.0
    angle_score = max(0.0, 1.0 - angle_dev / 45.0)

    sides = _side_lengths(ordered)
    horiz_ratio = min(sides[0], sides[2]) / max(sides[0], sides[2], 1.0)
    vert_ratio = min(sides[1], sides[3]) / max(sides[1], sides[3], 1.0)
    side_score = (horiz_ratio + vert_ratio) / 2.0

    border_hits = _corner_count_near_border(ordered, image_shape)
    border_penalty = border_hits / 4.0

    if _encompasses_outer_bbox(ordered, image_shape):
        bbox_penalty = 1.0
    else:
        bbox_penalty = 0.0

    """High-density edge / content score: real labels contain barcodes and
    printed text blocks, so a candidate with strong interior edge density is
    much more likely to be a sticker label than blank cardboard.
    """
    content_score = 0.0
    if gray is not None:
        edge_frac = _edge_density_ratio(ordered, gray)
        # Real label content (barcode + text) typically produces 0.05-0.30
        # interior edge fraction; blank surfaces stay well below 0.02.
        content_score = min(1.0, max(edge_frac, 0.0) / 0.12)

    pts_int = ordered.astype(np.int32)
    x_min = max(0, int(pts_int[:, 0].min()))
    x_max = min(width, int(pts_int[:, 0].max()) + 1)
    y_min = max(0, int(pts_int[:, 1].min()))
    y_max = min(height, int(pts_int[:, 1].max()) + 1)
    if x_max > x_min and y_max > y_min:
        roi = processed[y_min:y_max, x_min:x_max]
        edges = cv2.Canny(roi, 50, 150)
        edge_density = float(np.count_nonzero(edges)) / float(edges.size) if edges.size > 0 else 0.0
        edge_score = min(1.0, edge_density / 0.15)
    else:
        edge_score = 0.0

    w_avg = (sides[0] + sides[2]) / 2.0
    h_avg = (sides[1] + sides[3]) / 2.0
    rect_ratio = area / (w_avg * h_avg) if (w_avg * h_avg) > 0 else 0.0
    rect_bonus = min(0.1, (rect_ratio - 0.7) * 0.3) if rect_ratio > 0.7 else 0.0

    score = (
        0.20 * area_score
        + 0.20 * angle_score
        + 0.10 * side_score
        + 0.10 * edge_score
        + 0.20 * content_score
        + 0.10 * (1.0 - border_penalty)
        + 0.10 * (1.0 - bbox_penalty)
        + rect_bonus
    )
    return float(max(0.0, min(1.0, score)))


# ---------------------------------------------------------------------------
# Non-maximum suppression
# ---------------------------------------------------------------------------

def _bbox_iou(a: np.ndarray, b: np.ndarray) -> float:
    a_min = a.min(axis=0)
    a_max = a.max(axis=0)
    b_min = b.min(axis=0)
    b_max = b.max(axis=0)
    inter_min = np.maximum(a_min, b_min)
    inter_max = np.minimum(a_max, b_max)
    inter_size = np.maximum(inter_max - inter_min, 0.0)
    inter_area = float(inter_size[0] * inter_size[1])
    area_a = float((a_max[0] - a_min[0]) * (a_max[1] - a_min[1]))
    area_b = float((b_max[0] - b_min[0]) * (b_max[1] - b_min[1]))
    union = area_a + area_b - inter_area
    return inter_area / union if union > 0 else 0.0


def _nms_labels(
    labels: list[SingleLabel],
    iou_threshold: float = 0.3,
) -> list[SingleLabel]:
    sorted_labels = sorted(labels, key=lambda l: l.score, reverse=True)
    kept: list[SingleLabel] = []
    suppressed: set[int] = set()
    for i, label in enumerate(sorted_labels):
        if i in suppressed:
            continue
        kept.append(label)
        for j in range(i + 1, len(sorted_labels)):
            if j in suppressed:
                continue
            if _bbox_iou(label.corners, sorted_labels[j].corners) > iou_threshold:
                suppressed.add(j)
    return kept


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def detect_label(
    original_bgr: np.ndarray,
    max_dim: int = 1500,
    min_score: float = 0.25,
    max_labels: int = 10,
) -> LabelDetectionResult:
    debug: dict[str, Any] = {
        "contour_count": 0,
        "candidates": 0,
        "rejected": [],
    }

    height, width = original_bgr.shape[:2]
    longest = max(height, width)
    if longest > max_dim:
        sf = max_dim / float(longest)
        new_w = int(round(width * sf))
        new_h = int(round(height * sf))
        working = cv2.resize(original_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
    else:
        sf = 1.0
        working = original_bgr.copy()

    gray = cv2.cvtColor(working, cv2.COLOR_BGR2GRAY)
    processed = _preprocess_label(gray)
    contours = _extract_contours(processed)
    debug["contour_count"] = len(contours)

    work_h, work_w = working.shape[:2]
    image_area = float(work_h * work_w)
    min_area = 0.005 * image_area

    candidates: list[SingleLabel] = []
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
        valid, reason = _is_valid_label(ordered, working.shape, gray)
        if not valid:
            debug["rejected"].append(reason)
            continue

        score = _score_label(ordered, working.shape, processed, gray)
        if score >= min_score:
            candidates.append(SingleLabel(corners=ordered.copy(), score=score))

    if not candidates:
        return LabelDetectionResult(
            success=False,
            reason="No sticker label detected",
            debug=debug,
        )

    candidates = _nms_labels(candidates, iou_threshold=0.3)
    candidates = sorted(candidates, key=lambda l: l.score, reverse=True)[:max_labels]

    if sf != 1.0:
        for label in candidates:
            label.corners = (label.corners / sf).astype(np.float32)

    return LabelDetectionResult(
        success=True,
        labels=candidates,
        reason=f"{len(candidates)} label(s) detected",
        debug=debug,
    )
