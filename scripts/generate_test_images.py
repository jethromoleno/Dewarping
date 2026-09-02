"""Generate synthetic distorted test images for the warp correction pipeline."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def _make_document(width: int = 800, height: int = 1100) -> np.ndarray:
    """Create a simple white document with horizontal text lines."""
    doc = np.ones((height, width, 3), dtype=np.uint8) * 255
    for i, y in enumerate(range(80, height - 80, 60)):
        cv2.line(doc, (60, y), (width - 60, y), (30, 30, 30), 2)
        cv2.putText(
            doc,
            f"Sample line {i + 1}",
            (80, y + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (20, 20, 20),
            2,
        )
    cv2.rectangle(doc, (10, 10), (width - 10, height - 10), (0, 0, 0), 6)
    return doc


def generate_angled_document() -> np.ndarray:
    """Rectangular document photographed at an angle."""
    doc = _make_document(900, 700)
    h, w = doc.shape[:2]
    src = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
    dst = np.array([[120, 100], [1050, 80], [980, 820], [80, 780]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(doc, matrix, (1200, 900), borderValue=(40, 40, 40))


def generate_rotated_document() -> np.ndarray:
    """Slightly rotated document with mild perspective."""
    doc = _make_document(850, 650)
    h, w = doc.shape[:2]
    center = (w // 2, h // 2)
    rot = cv2.getRotationMatrix2D(center, 12, 1.0)
    rotated = cv2.warpAffine(doc, rot, (w, h), borderValue=(255, 255, 255))
    src = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
    dst = np.array([[150, 120], [1000, 160], [940, 820], [200, 780]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(rotated, matrix, (1100, 950), borderValue=(40, 40, 40))


def generate_strong_perspective() -> np.ndarray:
    """Strong trapezoidal perspective distortion."""
    doc = _make_document(700, 900)
    h, w = doc.shape[:2]
    src = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
    dst = np.array([[280, 120], [780, 200], [720, 820], [220, 760]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(doc, matrix, (1000, 900), borderValue=(40, 40, 40))


def generate_no_rectangle() -> np.ndarray:
    """Image with no obvious rectangular boundary."""
    return np.random.randint(30, 90, (600, 800, 3), dtype=np.uint8)


def generate_large_image() -> np.ndarray:
    """High-resolution synthetic document."""
    doc = _make_document(2400, 2600)
    h, w = doc.shape[:2]
    src = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
    dst = np.array([[450, 250], [3550, 400], [3400, 2750], [500, 2600]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(doc, matrix, (4000, 3000), borderValue=(40, 40, 40))


def generate_partial_border() -> np.ndarray:
    """Document not touching image edges."""
    doc = _make_document(500, 650)
    h, w = doc.shape[:2]
    src = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
    dst = np.array([[280, 130], [720, 150], [700, 780], [270, 760]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(doc, matrix, (1000, 900), borderValue=(40, 40, 40))


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    images = {
        "angled_document.jpg": generate_angled_document(),
        "rotated_document.jpg": generate_rotated_document(),
        "strong_perspective.jpg": generate_strong_perspective(),
        "no_rectangle.jpg": generate_no_rectangle(),
        "large_image.jpg": generate_large_image(),
        "partial_border.jpg": generate_partial_border(),
    }
    for name, image in images.items():
        path = FIXTURES_DIR / name
        cv2.imwrite(str(path), image)
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
