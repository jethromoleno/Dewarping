"""Robust, fail-safe text-orientation detection and upright correction.

Determines the net rotation (0/90/180/270 deg) of a cropped label purely from
image statistics and, when available, OCR/OSD and barcode detectors, so the
result is ALWAYS returned right-side up with left-to-right, top-to-bottom
readable text.  No hard-coded portrait/landscape assumption: the upright
output keeps the label's true aspect, so text and barcode are never distorted.

Orientation signal priority (fail-safe, each layer is independent):
  1. Tesseract OSD (``pytesseract.image_to_osd``) - most reliable, returns an
     exact 0/90/180/270 rotation angle.
  2. Barcode orientation (``cv2.barcode``) - when a barcode is present, its
     quadrilateral points give the barcode's own orientation axis.
  3. OpenCV text-axis analysis - gradient-orientation histogram resolves the
     {0,180} vs {90,270} family; ink-layout asymmetry resolves 0-vs-180 and
     90-vs-270.
"""

from __future__ import annotations

import cv2
import numpy as np

try:
    import pytesseract
    _HAS_TESSERACT = True
except Exception:  # pragma: no cover - tesseract not installed
    _HAS_TESSERACT = False

try:
    _detector = cv2.barcode.BarcodeDetector()
    _HAS_BARCODE = True
except Exception:  # pragma: no cover - barcode module unavailable
    _HAS_BARCODE = False


def _gray_and_edges(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blurred, 40, 120)
    return gray, edges


def _dark_fraction(gray: np.ndarray, y0: int, y1: int, threshold: int = 128) -> float:
    h = gray.shape[0]
    y1 = min(y1, h)
    if y1 <= y0:
        return 0.0
    band = gray[y0:y1]
    if band.size == 0:
        return 0.0
    return float(np.count_nonzero(band < threshold)) / float(band.size)


def _dark_fraction_x(gray: np.ndarray, x0: int, x1: int, threshold: int = 128) -> float:
    w = gray.shape[1]
    x1 = min(x1, w)
    if x1 <= x0:
        return 0.0
    band = gray[:, x0:x1]
    if band.size == 0:
        return 0.0
    return float(np.count_nonzero(band < threshold)) / float(band.size)


# ---------------------------------------------------------------------------
# 1. Tesseract OSD (primary)
# ---------------------------------------------------------------------------

def _osd_rotation_angle(image_bgr: np.ndarray) -> int | None:
    """Return the net rotation (0/90/180/270) reported by Tesseract OSD.

    Returns one of ``{0, 90, 180, 270}`` (the rotation needed to make the
    image upright), or ``None`` if Tesseract is unavailable / fails.
    """
    if not _HAS_TESSERACT:
        return None
    from PIL import Image as PILImage
    pil_img = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    try:
        osd = pytesseract.image_to_osd(PILImage.fromarray(pil_img))
    except Exception:
        return None
    for line in osd.splitlines():
        low = line.strip().lower()
        if low.startswith("rotate"):
            try:
                raw = int(round(float(line.split(":")[1].strip())))
                # OSD "rotate" is the clockwise rotation needed to make it
                # upright; normalize to a multiple of 90.
                normalized = (raw % 360 + 360) % 360
                nearest = [0, 90, 180, 270][min(range(4), key=lambda i: abs(normalized - [0, 90, 180, 270][i]))]
                return int(nearest)
            except Exception:
                return None
    return None


# ---------------------------------------------------------------------------
# 2. Barcode orientation (cv2.barcode)
# ---------------------------------------------------------------------------

def _barcode_rotation_angle(image_bgr: np.ndarray) -> int | None:
    """Estimate upright rotation from a detected barcode's quadrilateral.

    Barcodes are printed as vertical bar stripes.  A detected barcode's four
    corner points form a thin rectangle whose dominant axis is the barcode
    direction.  We rotate the crop so that axis is horizontal, then resolve
    the up/down ambiguity from the angle ordering.
    """
    if not _HAS_BARCODE:
        return None
    try:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        ok, decoded, points, _ = _detector.detectAndDecode(gray)
    except Exception:
        return None
    if not ok or points is None or len(points) == 0:
        return None
    pts = points[0].reshape(-1, 2)
    if pts.shape[0] < 2:
        return None

    # Dominant direction along the barcode's long axis.
    diffs = np.diff(pts, axis=0) if len(pts) > 2 else None
    if diffs is None:
        return None
    lengths = np.linalg.norm(diffs, axis=1)
    if lengths.size == 0:
        return None
    longest = diffs[int(np.argmax(lengths))]
    angle = float(np.degrees(np.arctan2(longest[1], longest[0])))
    # Snap to nearest 90: angle ~0 => already horizontal.
    cardinals = [0, 90, 180, 270]
    snapped = cardinals[min(range(4), key=lambda i: abs(angle - cardinals[i]))]
    # "snapped" is the current barcode axis angle.  Rotation to make it
    # horizontal (0 deg) is -snapped, normalized to a clockwise upright rot.
    rotation = (360 - snapped % 360) % 360
    correction = [0, 90, 180, 270][min(range(4), key=lambda i: abs(rotation - [0, 90, 180, 270][i]))]
    return int(correction)


# ---------------------------------------------------------------------------
# 3. OpenCV text-axis analysis (fallback)
# ---------------------------------------------------------------------------

def _dominant_text_axis(edges: np.ndarray, gray: np.ndarray) -> float:
    """Return the dominant gradient angle (deg, mod 180) of text-like edges.

    ~0 deg  -> text rows are horizontal (upright)
    ~90 deg -> text rows are vertical (sideways)
    """
    ddepth = cv2.CV_64F
    gx = cv2.Sobel(gray, ddepth, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, ddepth, 0, 1, ksize=3)

    mask = edges > 0
    if not np.any(mask):
        gx_m, gy_m = gx, gy
    else:
        gx_m, gy_m = gx * mask, gy * mask

    mag = np.hypot(gx_m, gy_m)
    angles = np.rad2deg(np.arctan2(gy_m, gx_m)) % 180.0
    ang_flat = angles[mag > 1.0]
    mag_flat = mag[mag > 1.0]
    if ang_flat.size == 0:
        return 0.0

    hist, _ = np.histogram(ang_flat, bins=90, range=(0, 180), weights=mag_flat)
    kernel = np.ones(3, dtype=np.float32) / 3.0
    hist = cv2.filter2D(hist, -1, kernel).flatten()
    peak_bin = int(np.argmax(hist))
    peak_angle = peak_bin * (180.0 / 90.0)
    return float(peak_angle)


def _global_ink_asymmetry(gray: np.ndarray, axis: str = "y") -> float | None:
    """Ratio of dark ink in the first half vs the whole image (minus 0.5).

    For ``axis="y"`` compares the top vs bottom halves; for ``axis="x"``
    compares the left vs right halves.  Returns a value in [-1, 1]:
      positive -> first half is ink-heavier (text upright toward it)
      negative -> second half is ink-heavier (needs a 180 flip)
      None      -> inconclusive (too little ink).
    """
    h, w = gray.shape
    if h < 48 or w < 24:
        return None
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ink = (binary > 0)
    total_ink = float(ink.sum())
    if total_ink < 8:
        return None
    if axis == "x":
        first = float(ink[:, : w // 2].sum())
    else:
        first = float(ink[: h // 2].sum())
    return float((first / total_ink - 0.5) * 2.0)


def _text_line_ink_bias(gray: np.ndarray) -> float | None:
    """Estimate upright vs inverted using per-line ink position.

    Upright text concentrates ink toward the top of each line (uppercase /
    ascenders); inverted text biases toward the bottom.  Returns [-1, 1]:
      positive -> top bias (upright), negative -> bottom bias (inverted).
    """
    h, w = gray.shape
    if h < 40 or w < 40:
        return None

    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    row_profile = (binary > 0).sum(axis=1).astype(np.float64)
    kernel = np.ones(7, dtype=np.float64) / 7.0
    smoothed = np.convolve(row_profile, kernel, mode="same")

    thr = max(4.0, 0.15 * float(smoothed.max(initial=0.0)))
    peaks = np.where(smoothed >= thr)[0]
    if peaks.size < 4:
        return None

    splits = np.where(np.diff(peaks) > int(max(2, h * 0.012)))[0]
    line_ranges = []
    start = peaks[0]
    for s in splits:
        line_ranges.append((start, peaks[s]))
        start = peaks[s + 1]
    line_ranges.append((start, peaks[-1]))

    biases: list[float] = []
    for y0, y1 in line_ranges:
        if y1 - y0 < 4:
            continue
        band = binary[y0:y1 + 1]
        dark = (band > 0).sum(axis=1).astype(np.float64)
        if dark.sum() < 8:
            continue
        total = float(dark.sum())
        if total <= 0:
            continue
        n = dark.size
        idx = np.arange(n, dtype=np.float64)
        centroid = float((idx * dark).sum()) / total
        norm = (0.5 - centroid / n) * 2.0  # +1 top, -1 bottom
        biases.append(norm)

    if len(biases) < 2:
        return None
    return float(np.mean(biases))


def _barcode_band_position(gray: np.ndarray, min_extent: float = 0.08) -> float | None:
    """Locate a dense, tall barcode band and return its vertical position.

    Barcode bars are tall, thin, closely-spaced VERTICAL strokes forming a
    contiguous horizontal band.  Distinguishing feature vs ordinary text: the
    barcode band is much TALLER and its rows are continuously edge-dense,
    whereas text lines are short, isolated bands separated by white gaps.

    Returns a normalized midline position in [0, 1] (0 = top, 1 = bottom) of
    the detected barcode band, or ``None`` if no clear barcode-like band
    (tall enough, wide enough) is found.
    """
    h, w = gray.shape
    if h < 48 or w < 48:
        return None
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    gx = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.hypot(gx, gy)
    verticality = np.abs(gx) / (mag + 1e-6)
    strong = mag > 10.0
    vert = (verticality > 0.8) & strong
    row_score = vert.mean(axis=1)

    thr = float(np.max(row_score)) * 0.4
    if thr < 0.03:
        return None

    # Find contiguous rows above threshold -> barcode is one tall run.
    runs = []
    in_run = False
    start = 0
    for i in range(h):
        above = row_score[i] > thr
        if above and not in_run:
            in_run = True
            start = i
        elif not above and in_run:
            in_run = False
            runs.append((start, i))
    if in_run:
        runs.append((start, h))

    if not runs:
        return None

    # Barcode is the tallest contiguous run that also spans a wide x-extent.
    best = None
    for (y0, y1) in runs:
        extent = (y1 - y0) / float(h)
        if extent < min_extent:
            continue
        # Check the run is horizontally wide (barcode spans most of the image).
        band = vert[y0:y1]
        row_sum = band.sum(axis=1)
        if float(row_sum.max(initial=0.0)) < 0.15 * w:
            continue
        if best is None or extent > best[1]:
            best = ((y0 + y1) / 2.0 / float(h), extent)
    if best is None:
        return None
    return best[0]


def _resolve_flip(
    gray: np.ndarray,
    image_bgr: np.ndarray | None = None,
    first_half_bias: float | None = None,
    line_bias: float | None = None,
    edge_top: float = 0.0,
    edge_bottom: float = 0.0,
) -> bool:
    """Decide whether the current (axis-aligned) crop needs a 180 flip.

    Signal priority (each is a confidence-gated independent check):
      1. Barcode-band position - shipping labels carry their barcode toward
         the bottom when upright, so a band in the top half => upside down.
      2. Global ink asymmetry - top half ink-heavier => upright.
      3. Text-line ink bias.
      4. Edge ink-darkness asymmetry (bold header near the top) - only trusted
         when the ratio is very strong to avoid the barcode false-positive.
    """
    # 1. Barcode-band position (most reliable for sticker/shipping labels).
    band_pos = _barcode_band_position(gray)
    if band_pos is not None:
        return band_pos < 0.5  # band in top half => needs a 180 flip

    # 2. Global ink asymmetry.
    if first_half_bias is not None and abs(first_half_bias) >= 0.10:
        return first_half_bias < 0.0

    # 3. Text-line ink bias.
    if line_bias is not None and abs(line_bias) >= 0.15:
        return line_bias < 0.0

    # 4. Edge ink-darkness asymmetry (bold header near the top).  Only trust
    #    a very strong ratio; a bottom barcode could otherwise look "bold".
    if not (edge_top <= 0.002 and edge_bottom <= 0.002):
        if edge_bottom > edge_top * 2.5 and edge_bottom > 0.01:
            return True
        if edge_top > edge_bottom * 2.5 and edge_top > 0.01:
            return False

    return False


def _opencv_rotation_angle(image_bgr: np.ndarray) -> int:
    """Pure-OpenCV fallback returning the upright rotation (0/90/180/270)."""
    gray, edges = _gray_and_edges(image_bgr)
    h, w = gray.shape[:2]

    axis = _dominant_text_axis(edges, gray)
    sideways = axis > 45.0 and axis < 135.0

    if not sideways:
        # Upright family {0, 180}.
        up_bias = _global_ink_asymmetry(gray, axis="y")
        line_bias = _text_line_ink_bias(gray)
        edge_top = _dark_fraction(gray, 0, int(h * 0.15))
        edge_bottom = _dark_fraction(gray, int(h * 0.85), h)
        if _resolve_flip(
            gray,
            image_bgr=image_bgr,
            first_half_bias=up_bias,
            line_bias=line_bias,
            edge_top=edge_top,
            edge_bottom=edge_bottom,
        ):
            return 180
        return 0

    # Sideways family {90, 270}: rotate to horizontal text first, then flip.
    rot_nonflip = cv2.rotate(image_bgr, cv2.ROTATE_90_CLOCKWISE)
    rgray = cv2.cvtColor(rot_nonflip, cv2.COLOR_BGR2GRAY)
    up_bias = _global_ink_asymmetry(rgray, axis="y")
    line_bias = _text_line_ink_bias(rgray)
    edge_top = _dark_fraction(rgray, 0, int(rgray.shape[0] * 0.15))
    edge_bottom = _dark_fraction(rgray, int(rgray.shape[0] * 0.85), rgray.shape[0])
    if _resolve_flip(
        rgray,
        image_bgr=rot_nonflip,
        first_half_bias=up_bias,
        line_bias=line_bias,
        edge_top=edge_top,
        edge_bottom=edge_bottom,
    ):
        return 270
    return 90


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_ROTATION_MAP = {
    0: None,
    90: cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}


def detect_rotation_angle(image_bgr: np.ndarray) -> int:
    """Fail-safe net upright rotation (one of 0/90/180/270) for ``image_bgr``.

    Layer order: Tesseract OSD -> cv2.barcode orientation -> OpenCV text-axis.
    The most confident available signal wins.
    """
    # Primary: Tesseract OSD.
    osd_angle = _osd_rotation_angle(image_bgr)
    if osd_angle is not None:
        return osd_angle

    # Secondary: barcode orientation.
    barcode_angle = _barcode_rotation_angle(image_bgr)
    if barcode_angle is not None and barcode_angle != 0:
        return barcode_angle

    # Fallback: OpenCV text-axis analysis.
    return _opencv_rotation_angle(image_bgr)


def correct_orientation(image_bgr: np.ndarray) -> np.ndarray:
    """Return a copy of ``image_bgr`` rotated so its text is strictly upright
    (right-side up, left-to-right / top-to-bottom readable)."""
    angle = detect_rotation_angle(image_bgr)
    if angle == 0 or angle is None:
        return image_bgr.copy()
    code = _ROTATION_MAP.get(angle)
    if code is None:
        return image_bgr.copy()
    return cv2.rotate(image_bgr, code)
