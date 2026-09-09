# Image Warp Correction

A full-stack web application that automatically detects and corrects perspective distortion in photographed documents and images. Built with **FastAPI** backend and **React + Vite** frontend.

## What It Does

- **Automatic mode:** Detects the largest plausible quadrilateral (document boundary) using OpenCV edge and contour analysis, then applies perspective correction.
- **Manual mode:** Drag four corner handles on a bounding box (top-left, top-right, bottom-right, bottom-left) when automatic detection fails or needs refinement.
- **Optional nonlinear correction:** Experimental mild radial undistortion after homography (clearly separate from perspective correction).

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS |
| Canvas | Fabric.js 5.x (quad editor) |
| Backend | FastAPI + Pydantic |
| Processing | OpenCV, NumPy, Pillow |
| Styling | Tailwind CSS + custom theme |

## Requirements

- Python 3.11+
- Node.js 18+

## Installation

**Backend:**
```bash
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

## Running

Start both servers (in separate terminals):

```bash
# Backend (port 8000)
python -m uvicorn backend.main:app --reload --port 8000

# Frontend (port 5173, proxies /api to backend)
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser.

> The Vite dev server proxies `/api` requests to the FastAPI backend automatically.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload an image, returns session ID |
| `POST` | `/api/detect` | Auto-detect document boundaries |
| `POST` | `/api/correct` | Run perspective correction |
| `POST` | `/api/manual-corners` | Update manual corner positions |
| `GET` | `/api/processing-info/{id}` | Get processing details |
| `GET` | `/api/images/{id}/original` | Serve original image |
| `GET` | `/api/images/{id}/corrected` | Serve corrected image |
| `GET` | `/api/images/{id}/corrected-download` | Download corrected as PNG |
| `GET` | `/api/health` | Health check |

## Project Structure

```
Dewarping/
├── backend/                        # FastAPI application
│   ├── main.py                     # App entry point + CORS
│   ├── schemas.py                  # Pydantic request/response models
│   ├── session_store.py            # In-memory image session store
│   ├── core/
│   │   └── config.py               # Application constants
│   ├── routes/
│   │   ├── processing.py           # Upload, detect, correct endpoints
│   │   └── images.py               # Image serving endpoints
│   └── services/
│       ├── correction_service.py   # Pipeline orchestration
│       └── image_service.py        # Image loading helpers
├── frontend/                       # React + Vite application
│   ├── package.json
│   ├── vite.config.js              # Dev server + API proxy
│   ├── tailwind.config.js          # Custom theme config
│   ├── index.html
│   └── src/
│       ├── main.jsx                # React entry point
│       ├── App.jsx                 # Main application
│       ├── api.js                  # Axios API client
│       ├── index.css               # Tailwind + custom styles
│       └── components/
│           ├── Sidebar.jsx         # Mode selection + settings
│           ├── ImageUploader.jsx   # Drag & drop upload
│           ├── QuadEditor.jsx      # Fabric.js canvas editor
│           ├── ImageComparison.jsx # Side-by-side view
│           ├── ProcessingInfo.jsx  # Details panel
│           ├── Spinner.jsx         # Loading overlay
│           └── Toast.jsx           # Notifications
├── processing/                     # Image processing pipeline
│   ├── preprocessing.py            # Grayscale, denoise, CLAHE
│   ├── detection.py                # Contour-based quad detection
│   ├── perspective.py              # Homography rectification
│   └── nonlinear.py                # Experimental post-homography
├── utils/                          # Shared utilities
│   ├── image_utils.py              # Load, scale, encode, ordering
│   └── canvas_utils.py             # Coordinate conversion
├── scripts/
│   └── generate_test_images.py     # Synthetic test fixtures
└── tests/
    └── fixtures/                   # Test images
```

## User Manual

Step-by-step usage (upload, automatic label extraction, manual corners, download, and troubleshooting) is in **[USER_MANUAL.md](USER_MANUAL.md)**.

## Example Workflow

1. Start the backend: `python -m uvicorn backend.main:app --reload --port 8000`
2. Start the frontend: `cd frontend && npm run dev`
3. Open `http://localhost:5173`
4. Drag and drop a distorted document photo (or click to browse)
5. **Automatic:** Click **Extract Label** to crop a sticker, or **Detect Boundaries** to find a document quad
6. **Manual:** Drag the red corner handles to the document edges, then click **Correct Image**
7. Compare original and result side by side
8. Expand **Processing Details** to inspect timing and homography
9. Click **Download Corrected Image** to save
10. Click **New Image** to process another file

## Perspective Correction

1. Four corner points define the distorted document boundary
2. `cv2.getPerspectiveTransform()` computes the 3x3 homography matrix
3. `cv2.warpPerspective()` resamples the image into a front-facing rectangle

Output dimensions are derived from detected edge lengths, not hardcoded values. Detection runs on a downscaled copy for speed; the final warp uses full resolution.

## Known Limitations

- Nonlinear warping (curved pages, severe barrel distortion) cannot be fully reversed without ML models
- Automatic detection may fail on low-contrast edges, cluttered backgrounds, or glossy reflections
- Manual mode requires accurate handle placement; small errors affect output quality
