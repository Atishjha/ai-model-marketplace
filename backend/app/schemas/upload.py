from typing import Optional

from pydantic import BaseModel, ConfigDict


class UploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cid: str
    filename: str
    size_bytes: int
    gateway_url: str


class SignedUrlRequest(BaseModel):
    filename: Optional[str] = None
    content_type: Optional[str] = None


class SignedUrlResponse(BaseModel):
    url: str
    expires_in: int
