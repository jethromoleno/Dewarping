"""Pydantic schemas for API request/response contracts."""

from __future__ import annotations

from pydantic import BaseModel


class UploadResponse(BaseModel):
    image_id: str
    width: int
    height: int


class DetectRequest(BaseModel):
    image_id: str


class DetectResponse(BaseModel):
    success: bool
    corners: list[list[float]] | None = None
    score: float = 0.0
    reason: str = ""


class LabelDetectRequest(BaseModel):
    image_id: str


class SingleLabelInfo(BaseModel):
    index: int
    score: float
    output_size: list[int] | None = None


class LabelDetectResponse(BaseModel):
    success: bool
    labels: list[SingleLabelInfo] = []
    reason: str = ""
    extraction_time_ms: float = 0.0


class CorrectRequest(BaseModel):
    image_id: str
    corners: list[list[float]]
    enable_nonlinear: bool = False
    mode: str = "automatic"


class CorrectResponse(BaseModel):
    success: bool
    source_size: list[int]
    output_size: list[int]
    total_time_ms: float


class ManualCornersRequest(BaseModel):
    image_id: str
    corners: list[list[float]]


class ManualCornersResponse(BaseModel):
    corners: list[list[float]]


class ProcessingInfoResponse(BaseModel):
    detection: dict
    perspective: dict
    nonlinear: dict
    total_time_ms: float
