# Image Warp Correction

A local Streamlit application that automatically detects and corrects perspective distortion in photographed documents and images. Upload a warped image, apply homography-based rectification, and download the corrected result.

## What It Does

- **Automatic mode:** Detects the largest plausible quadrilateral (document boundary) using OpenCV edge and contour analysis, then applies perspective correction.
- **Manual mode:** Drag four corner handles on a bounding box (top-left, top-right, bottom-right, bottom-left) when automatic detection fails or needs refinement.
- **Optional nonlinear correction:** Experimental mild radial undistortion after homography (clearly separate from perspective correction).

Supported distortion types for v1:

- Rotation and skew
- Angled photography
- Perspective (trapezoid) distortion
- Mild geometric warping

## Requirements

- Python 3.11+
- See `requirements.txt`

## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
python -m streamlit run app.py
```

Open the URL shown in the terminal (typically `http://localhost:8501`).

> **Windows note:** If `streamlit` is not recognized, use `python -m streamlit run app.py` instead. This works even when Python's `Scripts` folder is not on your PATH.

## Example Workflow

1. Launch the app with `python -m streamlit run app.py`.
2. Upload a distorted document photo (PNG, JPG, JPEG, or WebP).
3. Leave **Correction mode** on **Automatic** and click **Correct Image**.
4. Compare the original and corrected previews side by side.
5. Expand **Processing Details** to inspect corners, homography matrix, and timing.
6. Click **Download Corrected Image** to save the result.
7. If automatic detection fails, switch to **Manual**, drag the green corner handles to the document edges, then click **Correct Image** again.
8. To process another file, click **Upload New Image** in the sidebar (no page refresh needed).

## Perspective Correction Explained

Perspective correction maps a quadrilateral region in the source image to a rectangle using a **homography** (3×3 projective transform):

1. Four corner points define the distorted document boundary.
2. `cv2.getPerspectiveTransform()` computes the transform matrix.
3. `cv2.warpPerspective()` resamples the image into a front-facing rectangle.

Output dimensions are derived from the detected edge lengths, not hard-coded values. Detection runs on a downscaled working copy for speed; the final warp uses the full-resolution image.

## Project Structure

```text
├── app.py                      # Streamlit UI
├── requirements.txt
├── README.md
├── processing/
│   ├── preprocessing.py        # Grayscale, denoise, CLAHE
│   ├── detection.py            # Contour-based quad detection
│   ├── perspective.py          # Homography rectification
│   └── nonlinear.py            # Experimental post-homography correction
├── utils/
│   ├── image_utils.py          # Load, scale, encode, point ordering
│   └── canvas_utils.py         # Draggable bbox canvas helpers
├── scripts/
│   └── generate_test_images.py # Synthetic test fixtures
└── tests/
    └── test_pipeline.py
```

## Testing

Generate synthetic test images and run the test suite:

```bash
python scripts/generate_test_images.py
pytest tests/ -v
```

Test scenarios covered:

1. Angled document
2. Rotated document
3. Strong perspective distortion
4. Image with no rectangular boundary
5. Large high-resolution image
6. Partial border / manual corner rectification

## Known Limitations

- **Nonlinear warping** (curved pages, severe barrel distortion) cannot be fully reversed without additional information or ML models.
- Automatic detection may fail on low-contrast edges, cluttered backgrounds, or glossy reflections.
- The experimental nonlinear stage applies only mild radial undistortion; it is not a full dewarping solution.
- Manual mode requires accurate handle placement on document edges; small errors affect output quality.

## Future Improvements

The modular layout supports swapping or extending components without rewriting the UI:

- Deep-learning-based corner detection
- Document segmentation
- Optical-flow-based deformation estimation
- Thin-plate spline registration
- Learned image restoration
- Feature-based image registration
- Automatic distortion classification

## Troubleshooting

- **`streamlit` is not recognized (Windows):** Run `python -m streamlit run app.py` instead of `streamlit run app.py`.
- **Automatic detection fails:** Use Manual mode and drag the four corner handles to the document edges.
- **Canvas handles hard to select:** Zoom your browser if needed; drag the green circles, not the outline.
- **`image_to_url` AttributeError in Manual mode:** Reinstall deps with `pip install -r requirements.txt`. This project uses `streamlit-drawable-canvas-fix` (not the unmaintained `streamlit-drawable-canvas`) for Streamlit 1.41+ compatibility.
- **Upload another image:** Click **Upload New Image** in the sidebar to reset and open a fresh file picker.
- **Large images slow to process:** Detection uses a working copy; only the final warp runs at full resolution.
