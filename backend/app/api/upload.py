import time

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.schemas.upload import SignedUrlRequest, SignedUrlResponse, UploadResponse

router = APIRouter(prefix="/upload", tags=["upload"])

PINATA_PIN_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"
PINATA_SIGN_URL = "https://uploads.pinata.cloud/v3/files/sign"
SIGNED_URL_TTL_SECONDS = 60


def _measure_and_rewind(f) -> int:
    """Blocking seek/tell, run off the event loop via run_in_threadpool below."""
    f.seek(0, 2)
    size = f.tell()
    f.seek(0)
    return size


@router.post("/signed-url", response_model=SignedUrlResponse)
async def get_signed_upload_url(request: Request, body: SignedUrlRequest) -> SignedUrlResponse:
    """
    Mints a short-lived Pinata upload URL so the browser can upload a model
    file directly to IPFS — bytes never pass through this backend, and
    PINATA_JWT never leaves the server. Preferred path for actual model
    weight files; see POST /upload for the small-file relay alternative.
    """
    settings = get_settings()
    if not settings.PINATA_JWT:
        raise HTTPException(status_code=500, detail="PINATA_JWT is not configured on the server")

    payload: dict = {
        "date": int(time.time()),
        "expires": SIGNED_URL_TTL_SECONDS,
        "max_file_size": settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024,
    }
    if body.filename:
        payload["filename"] = body.filename
    if body.content_type:
        payload["allow_mime_types"] = [body.content_type]

    client = request.app.state.http_client
    try:
        response = await client.post(
            PINATA_SIGN_URL,
            headers={"Authorization": f"Bearer {settings.PINATA_JWT}"},
            json=payload,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach IPFS pinning service: {exc}") from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to create signed upload URL ({response.status_code}): {response.text}",
        )

    data = response.json()
    signed_url = data.get("data") if isinstance(data, dict) else data
    if not isinstance(signed_url, str):
        raise HTTPException(status_code=502, detail=f"Unexpected response shape from Pinata: {data}")

    return SignedUrlResponse(url=signed_url, expires_in=SIGNED_URL_TTL_SECONDS)


@router.post("", response_model=UploadResponse)
async def upload_model(request: Request, file: UploadFile = File(...)) -> UploadResponse:
    """
    Relay upload using Pinata's legacy key+secret auth: file passes through
    this backend before reaching Pinata. Fine for small files (thumbnails,
    metadata); for model weight files prefer POST /upload/signed-url.
    """
    settings = get_settings()
    if not (settings.PINATA_API_KEY and settings.PINATA_SECRET_API_KEY):
        raise HTTPException(
            status_code=500,
            detail="PINATA_API_KEY / PINATA_SECRET_API_KEY are not configured on the server",
        )

    size_bytes = await run_in_threadpool(_measure_and_rewind, file.file)
    if size_bytes == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds max upload size of {settings.MAX_UPLOAD_SIZE_MB}MB")

    client = request.app.state.http_client
    try:
        response = await client.post(
            PINATA_PIN_URL,
            headers={
                "pinata_api_key": settings.PINATA_API_KEY,
                "pinata_secret_api_key": settings.PINATA_SECRET_API_KEY,
            },
            files={"file": (file.filename, file.file, file.content_type)},
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach IPFS pinning service: {exc}") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"IPFS pin failed ({response.status_code}): {response.text}")

    data = response.json()
    cid = data["IpfsHash"]

    return UploadResponse(
        cid=cid,
        filename=file.filename or "unnamed",
        size_bytes=size_bytes,
        gateway_url=f"{settings.PINATA_GATEWAY}/{cid}",
    )
