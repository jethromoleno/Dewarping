"""Streamlit UI for Image Warp Correction."""

from __future__ import annotations

import base64
import io
import time

import cv2
import numpy as np
import streamlit as st
from PIL import Image

from components.quad_editor import quad_editor
from processing.detection import detect_document_quad
from processing.nonlinear import apply_nonlinear_correction
from processing.perspective import rectify_perspective
from utils.canvas_utils import display_corners_to_full
from utils.image_utils import (
    bgr_to_rgb,
    create_working_copy,
    default_inset_corners,
    draw_corners_overlay,
    encode_image_png,
    load_image_bytes,
    order_points,
    scale_corners_to_display,
    scale_points,
)

CANVAS_MAX_WIDTH = 700


def _init_session_state() -> None:
    defaults = {
        "original_bgr": None,
        "corrected_bgr": None,
        "corners": None,
        "processing_info": None,
        "auto_failed": False,
        "manual_corners": None,
        "manual_editor_key": 0,
        "manual_display_corners": None,
        "suggested_corners": None,
        "scale_factor": 1.0,
        "uploader_key": 0,
        "loaded_file_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_results() -> None:
    st.session_state.corrected_bgr = None
    st.session_state.corners = None
    st.session_state.processing_info = None
    st.session_state.auto_failed = False


def _display_image_data_url(image_rgb: np.ndarray) -> str:
    """Encode an RGB image as a PNG data URL for the quad editor background."""
    buffer = io.BytesIO()
    Image.fromarray(image_rgb).save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _set_manual_corners(image_bgr: np.ndarray, corners: np.ndarray) -> None:
    """Sync full-resolution and display-space manual corners."""
    _, _, display_scale = _canvas_display_scale(image_bgr)
    ordered = order_points(corners).astype(np.float32)
    st.session_state.manual_corners = ordered
    st.session_state.manual_display_corners = scale_corners_to_display(
        ordered,
        display_scale,
    ).tolist()


def _reset_manual_bbox(image_bgr: np.ndarray) -> None:
    height, width = image_bgr.shape[:2]
    _set_manual_corners(image_bgr, default_inset_corners(width, height))
    st.session_state.manual_editor_key += 1


def _clear_upload_state() -> None:
    st.session_state.original_bgr = None
    st.session_state.corrected_bgr = None
    st.session_state.corners = None
    st.session_state.processing_info = None
    st.session_state.auto_failed = False
    st.session_state.manual_corners = None
    st.session_state.manual_display_corners = None
    st.session_state.manual_editor_key += 1
    st.session_state.suggested_corners = None
    st.session_state.loaded_file_id = None
    st.session_state.uploader_key += 1


def _ensure_manual_corners(image_bgr: np.ndarray) -> None:
    if st.session_state.manual_corners is None:
        _reset_manual_bbox(image_bgr)


def _resolve_manual_corners(image_bgr: np.ndarray) -> np.ndarray:
    """Return the freshest full-resolution manual corners available."""
    if st.session_state.manual_corners is not None:
        return order_points(st.session_state.manual_corners)
    _ensure_manual_corners(image_bgr)
    return order_points(st.session_state.manual_corners)


def _run_correction(
    original_bgr: np.ndarray,
    corners: np.ndarray,
    enable_nonlinear: bool,
    detection_info: dict | None = None,
) -> None:
    """Apply perspective correction and optional nonlinear stage."""
    total_start = time.perf_counter()

    corrected, perspective_info = rectify_perspective(original_bgr, corners)
    corrected, nonlinear_info = apply_nonlinear_correction(
        corrected,
        enabled=enable_nonlinear,
    )

    total_ms = (time.perf_counter() - total_start) * 1000.0
    st.session_state.corrected_bgr = corrected
    st.session_state.corners = corners
    st.session_state.processing_info = {
        "detection": detection_info or {},
        "perspective": perspective_info,
        "nonlinear": nonlinear_info,
        "total_time_ms": total_ms,
    }


def _canvas_display_scale(image_bgr: np.ndarray) -> tuple[int, int, float]:
    height, width = image_bgr.shape[:2]
    display_width = min(CANVAS_MAX_WIDTH, width)
    display_scale = display_width / float(width)
    display_height = int(round(height * display_scale))
    return display_width, display_height, display_scale


def _render_manual_bbox_editor(image_bgr: np.ndarray) -> np.ndarray:
    """Interactive single-shape quadrilateral editor with draggable vertices."""
    st.subheader("Manual Bounding Box")
    st.caption("Drag any green corner of the box. The outline and handles move together.")

    _ensure_manual_corners(image_bgr)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Reset Box", key="reset_manual_bbox"):
            _reset_manual_bbox(image_bgr)
            st.rerun()
    with col2:
        if st.button(
            "Use Auto-Detected Box",
            key="use_auto_detected_box",
            disabled=st.session_state.suggested_corners is None,
        ):
            _set_manual_corners(image_bgr, st.session_state.suggested_corners.copy())
            st.session_state.manual_editor_key += 1
            st.rerun()
    with col3:
        if st.session_state.manual_corners is not None:
            st.write("Corners: 4/4")

    display_width, display_height, display_scale = _canvas_display_scale(image_bgr)
    display_bgr = cv2.resize(image_bgr, (display_width, display_height), interpolation=cv2.INTER_AREA)
    background_data_url = _display_image_data_url(bgr_to_rgb(display_bgr))

    editor_corners = quad_editor(
        background_data_url=background_data_url,
        corners=st.session_state.manual_display_corners,
        height=display_height,
        width=display_width,
        editor_key=str(st.session_state.manual_editor_key),
        key=f"manual_quad_editor_{st.session_state.manual_editor_key}",
    )

    if editor_corners is not None and len(editor_corners) == 4:
        full_corners = display_corners_to_full(editor_corners, display_scale)
        st.session_state.manual_corners = full_corners
        st.session_state.manual_display_corners = scale_corners_to_display(
            full_corners,
            display_scale,
        ).tolist()

    return _resolve_manual_corners(image_bgr)


def main() -> None:
    st.set_page_config(page_title="Image Warp Correction", layout="wide")
    _init_session_state()

    st.title("Image Warp Correction")
    st.write(
        "Upload a distorted image to automatically straighten perspective "
        "or manually adjust a bounding box."
    )

    if st.sidebar.button("Upload New Image"):
        _clear_upload_state()
        st.rerun()

    uploaded = st.file_uploader(
        "Upload an image",
        type=["png", "jpg", "jpeg", "webp"],
        key=f"image_uploader_{st.session_state.uploader_key}",
    )

    if uploaded is not None:
        file_id = f"{uploaded.name}_{uploaded.size}"
        if st.session_state.get("loaded_file_id") != file_id:
            st.session_state.loaded_file_id = file_id
            st.session_state.original_bgr = load_image_bytes(uploaded.getvalue())
            _reset_results()
            st.session_state.manual_corners = None
            st.session_state.manual_display_corners = None
            st.session_state.manual_editor_key += 1
            st.session_state.suggested_corners = None

    original = st.session_state.original_bgr
    if original is None:
        st.info("Upload an image to begin.")
        return

    st.sidebar.header("Settings")
    mode = st.sidebar.radio("Correction mode", ["Automatic", "Manual"], index=0)
    enable_nonlinear = st.sidebar.checkbox(
        "Enable advanced nonlinear correction",
        value=False,
        help="Experimental post-homography correction. Cannot fully reverse arbitrary warping.",
    )

    if mode == "Manual":
        _render_manual_bbox_editor(original)

    if st.sidebar.button("Correct Image", type="primary"):
        _reset_results()

        if mode == "Automatic":
            working, scale_factor = create_working_copy(original)
            st.session_state.scale_factor = scale_factor

            detection = detect_document_quad(working)
            if detection.corners is not None:
                full_corners = scale_points(detection.corners, scale_factor)
                st.session_state.suggested_corners = full_corners

            if not detection.success or detection.corners is None:
                st.session_state.auto_failed = True
                st.warning(
                    "Automatic boundary detection failed. Try Manual Correction."
                )
            else:
                _run_correction(
                    original,
                    full_corners,
                    enable_nonlinear,
                    detection_info={
                        "mode": "automatic",
                        "score": detection.score,
                        "reason": detection.reason,
                        "working_scale_factor": scale_factor,
                        "debug": detection.debug,
                    },
                )
                st.success("Image corrected successfully.")

        else:
            _ensure_manual_corners(original)
            corners = _resolve_manual_corners(original)
            _run_correction(
                original,
                corners,
                enable_nonlinear,
                detection_info={"mode": "manual"},
            )
            _set_manual_corners(original, corners)
            st.success("Image corrected successfully.")

    if st.session_state.auto_failed and mode == "Automatic":
        st.info("Switch to **Manual** mode in the sidebar to adjust the bounding box.")

    st.divider()
    col_orig, col_corr = st.columns(2)

    with col_orig:
        st.subheader("Original")
        orig_display = original
        if st.session_state.corners is not None:
            orig_display = draw_corners_overlay(original, st.session_state.corners)
        st.image(bgr_to_rgb(orig_display), use_container_width=True)

    with col_corr:
        st.subheader("Corrected")
        if st.session_state.corrected_bgr is not None:
            st.image(
                bgr_to_rgb(st.session_state.corrected_bgr),
                use_container_width=True,
            )
            png_bytes = encode_image_png(st.session_state.corrected_bgr)
            st.download_button(
                label="Download Corrected Image",
                data=png_bytes,
                file_name="corrected_image.png",
                mime="image/png",
            )
        else:
            st.caption("Corrected image will appear here.")

    info = st.session_state.processing_info
    if info:
        with st.expander("Processing Details", expanded=False):
            st.write("**Source dimensions:**", info["perspective"]["input_size"])
            st.write("**Output dimensions:**", info["perspective"]["output_size"])
            st.write("**Detected corners (TL, TR, BR, BL):**")
            st.code(info["perspective"]["source_corners"])
            st.write("**Homography matrix:**")
            st.code(info["perspective"]["homography_matrix"])
            st.write(
                f"**Perspective time:** {info['perspective']['perspective_time_ms']:.1f} ms"
            )
            st.write(f"**Total time:** {info['total_time_ms']:.1f} ms")

            detection = info.get("detection", {})
            if detection.get("mode") == "automatic":
                st.write(f"**Detection score:** {detection.get('score', 0):.3f}")
                st.write(f"**Detection reason:** {detection.get('reason', '')}")
                if detection.get("debug"):
                    st.write("**Detection debug:**")
                    st.json(detection["debug"])

            nonlinear = info.get("nonlinear", {})
            st.write(f"**Nonlinear correction applied:** {nonlinear.get('applied', False)}")
            if nonlinear.get("applied"):
                st.write(f"**Nonlinear method:** {nonlinear.get('method')}")
                st.caption(nonlinear.get("note", ""))


if __name__ == "__main__":
    main()
