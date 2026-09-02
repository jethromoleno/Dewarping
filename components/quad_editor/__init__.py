"""Streamlit component: single quadrilateral with draggable corner vertices."""

from __future__ import annotations

import os

import streamlit.components.v1 as components

parent_dir = os.path.dirname(os.path.abspath(__file__))
_component_func = components.declare_component(
    "quad_editor",
    path=os.path.join(parent_dir, "frontend"),
)


def quad_editor(
    *,
    background_data_url: str,
    corners: list[list[float]],
    height: int,
    width: int,
    editor_key: str,
    key: str | None = None,
) -> list[list[float]] | None:
    """
    Render a quadrilateral editor over a background image.

    Returns display-space corner coordinates [[x, y], ...] (TL, TR, BR, BL order
    is applied on the Python side) or None before the first interaction.
    """
    result = _component_func(
        backgroundDataUrl=background_data_url,
        corners=corners,
        canvasHeight=height,
        canvasWidth=width,
        editorKey=editor_key,
        key=key,
        default=None,
    )
    if result is None:
        return None
    if isinstance(result, dict) and result.get("status") == "error":
        return None
    if isinstance(result, dict):
        corners_result = result.get("corners")
        if corners_result is not None:
            return corners_result
    return None
