"""API routes for image upload, correction, and detection."""

from __future__ import annotations

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.schemas import (
    CorrectRequest,
    CorrectResponse,
    DetectRequest,
    DetectResponse,
    LabelDetectRequest,
    LabelDetectResponse,
    ManualCornersRequest,
    ManualCornersResponse,
    ProcessingInfoResponse,
    UploadResponse,
)
from backend.session_store import create_session, get_session
from backend.services.correction_service import run_correction
from backend.services.image_service import load_uploaded_image
from utils.image_utils import order_points

DISPLAY_MAX_WIDTH = 700

router = APIRouter(tags=["processing"])


@router.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)) -> UploadResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    contents = await file.read()
    try:
        image_bgr = load_uploaded_image(contents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    session = create_session(image_bgr)
    height, width = image_bgr.shape[:2]
    return UploadResponse(image_id=session.image_id, width=width, height=height)


@router.post("/detect", response_model=DetectResponse)
def detect_boundaries(req: DetectRequest) -> DetectResponse:
    session = get_session(req.image_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Image session not found.")

    original = session.original_bgr
    height, width = original.shape[:2]
    max_dim = 1500
    longest = max(height, width)

    if longest > max_dim:
        scale_factor = max_dim / float(longest)
        new_w = int(round(width * scale_factor))
        new_h = int(round(height * scale_factor))
        working = cv2.resize(original, (new_w, new_h), interpolation=cv2.INTER_AREA)
    else:
        scale_factor = 1.0
        working = original.copy()

    from processing.detection import detect_document_quad

    detection = detect_document_quad(working)

    if detection.corners is not None and detection.success:
        from utils.image_utils import scale_points

        full_corners = scale_points(detection.corners, scale_factor)
        session.suggested_corners = full_corners

    return DetectResponse(
        success=detection.success,
        corners=detection.corners.tolist() if detection.corners is not None and detection.success else None,
        score=detection.score,
        reason=detection.reason,
    )


@router.post("/detect-label", response_model=LabelDetectResponse)
def detect_label_endpoint(req: LabelDetectRequest) -> LabelDetectResponse:
    session = get_session(req.image_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Image session not found.")

    from processing.label_detection import detect_label
    from processing.scanner import extract_label_scanned
    from utils.image_utils import order_points as _order_points

    result = detect_label(session.original_bgr)

    if not result.success or not result.labels:
        return LabelDetectResponse(
            success=False,
            reason=result.reason,
        )

    # Return ONLY ONE detected and cropped label per scan: pick the single
    # highest-scoring label candidate.
    best_label = result.labels[0]

    scanned, info = extract_label_scanned(session.original_bgr, best_label.corners)

    session.label_corrected_images = [scanned]
    first_corners = _order_points(best_label.corners)
    session.corners = first_corners
    session.suggested_corners = best_label.corners

    return LabelDetectResponse(
        success=True,
        labels=[
            {
                "index": 0,
                "score": best_label.score,
                "output_size": list(info.get("final_size", [0, 0])),
            }
        ],
        reason=result.reason,
        extraction_time_ms=info.get("total_ms", 0.0),
    )


@router.post("/correct", response_model=CorrectResponse)
def correct_image(req: CorrectRequest) -> CorrectResponse:
    session = get_session(req.image_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Image session not found.")

    display_corners = np.array(req.corners, dtype=np.float32).reshape(4, 2)

    orig_h, orig_w = session.original_bgr.shape[:2]
    display_scale = min(DISPLAY_MAX_WIDTH, orig_w) / float(orig_w)
    full_corners = (display_corners / display_scale).astype(np.float32)

    run_correction(
        session=session,
        corners=full_corners,
        enable_nonlinear=req.enable_nonlinear,
        detection_info={"mode": req.mode},
    )

    info = session.processing_info or {}
    perspective = info.get("perspective", {})

    return CorrectResponse(
        success=True,
        source_size=list(perspective.get("input_size", [0, 0])),
        output_size=list(perspective.get("output_size", [0, 0])),
        total_time_ms=info.get("total_time_ms", 0.0),
    )


@router.post("/manual-corners", response_model=ManualCornersResponse)
def update_manual_corners(req: ManualCornersRequest) -> ManualCornersResponse:
    session = get_session(req.image_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Image session not found.")

    corners = order_points(np.array(req.corners, dtype=np.float32).reshape(4, 2))
    session.manual_corners = corners
    return ManualCornersResponse(corners=corners.tolist())


@router.get("/processing-info/{image_id}", response_model=ProcessingInfoResponse)
def get_processing_info(image_id: str) -> ProcessingInfoResponse:
    session = get_session(image_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Image session not found.")

    info = session.processing_info
    if info is None:
        raise HTTPException(status_code=404, detail="No processing info available.")

    return ProcessingInfoResponse(
        detection=info.get("detection", {}),
        perspective=info.get("perspective", {}),
        nonlinear=info.get("nonlinear", {}),
        total_time_ms=info.get("total_time_ms", 0.0),
    )
