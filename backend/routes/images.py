"""Image serving routes."""

from __future__ import annotations

import io

import cv2
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.session_store import get_session
from utils.image_utils import draw_corners_overlay, encode_image_png

router = APIRouter(tags=["images"])


def _serve_bgr_image(image_bgr) -> StreamingResponse:
    success, buffer = cv2.imencode(".jpg", image_bgr, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not success:
        raise HTTPException(status_code=500, detail="Failed to encode image.")
    return StreamingResponse(
        io.BytesIO(buffer.tobytes()),
        media_type="image/jpeg",
    )


@router.get("/images/{image_id}/original")
def serve_original(image_id: str) -> StreamingResponse:
    session = get_session(image_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Image not found.")
    return _serve_bgr_image(session.original_bgr)


@router.get("/images/{image_id}/original-overlay")
def serve_original_overlay(image_id: str) -> StreamingResponse:
    session = get_session(image_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Image not found.")

    if session.corners is not None:
        display = draw_corners_overlay(session.original_bgr, session.corners)
    else:
        display = session.original_bgr
    return _serve_bgr_image(display)


@router.get("/images/{image_id}/corrected")
def serve_corrected(image_id: str) -> StreamingResponse:
    session = get_session(image_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Image not found.")
    if session.corrected_bgr is None:
        raise HTTPException(status_code=404, detail="Corrected image not available.")
    return _serve_bgr_image(session.corrected_bgr)


@router.get("/images/{image_id}/label/{index}")
def serve_label(image_id: str, index: int) -> StreamingResponse:
    session = get_session(image_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Image not found.")
    if not session.label_corrected_images or index >= len(session.label_corrected_images):
        raise HTTPException(status_code=404, detail="Label not available.")
    return _serve_bgr_image(session.label_corrected_images[index])


@router.get("/images/{image_id}/corrected-download")
def download_corrected(image_id: str) -> StreamingResponse:
    session = get_session(image_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Image not found.")
    if session.corrected_bgr is None:
        raise HTTPException(status_code=404, detail="Corrected image not available.")

    png_bytes = encode_image_png(session.corrected_bgr)
    return StreamingResponse(
        io.BytesIO(png_bytes),
        media_type="image/png",
        headers={"Content-Disposition": "attachment; filename=corrected_image.png"},
    )


@router.get("/images/{image_id}/display")
def serve_display(image_id: str) -> StreamingResponse:
    session = get_session(image_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Image not found.")

    height, width = session.original_bgr.shape[:2]
    max_w = 700
    if width > max_w:
        scale = max_w / float(width)
        new_w = max_w
        new_h = int(round(height * scale))
        display = cv2.resize(session.original_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
    else:
        display = session.original_bgr

    success, buffer = cv2.imencode(".png", display)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to encode image.")
    return StreamingResponse(
        io.BytesIO(buffer.tobytes()),
        media_type="image/png",
    )
