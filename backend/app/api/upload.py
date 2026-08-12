from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.schemas.upload import SignedUrlRequest, SignedUrlResponse, UploadResponse

router = APIRouter()

PINATA_PIN_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"
PINATA_SIGN_URL = "https://uploads.pinata.cloud/v3/files/sign"

SIGNED_URL_TTL_SECONDS = 60  # short-lived: just long enough for the client to start the upload


def _measure_and_rewind(f) -> int:
    """Blocking seek/tell, run off the event loop via run_in_threadpool below."""
    f.seek(0, 2)  # end
    size = f.tell()
    f.seek(0)  # rewind for the upload that follows
    return size


@router.post("/upload/signed-url", response_model=SignedUrlResponse)
async def get_signed_upload_url(request: Request, body: SignedUrlRequest) -> SignedUrlResponse:
    """
    Mints a short-lived, scoped Pinata upload URL. The browser uploads the
    model file directly to this URL — the file's bytes never pass through
    this backend at all, and PINATA_JWT never leaves the server.

    This replaces the relay pattern in /upload for the actual model files:
    that endpoint still exists and is fine for small files, but for
    multi-gigabyte model weights this is the version that actually scales,
    since our server no longer sits in the request path for the transfer.
    """
    if not settings.pinata_jwt:
        raise HTTPException(
            status_code=500,
            detail="PINATA_JWT is not configured on the server",
        )

    import time

    payload: dict = {
        "date": int(time.time()),
        "expires": SIGNED_URL_TTL_SECONDS,
        "max_file_size": settings.max_upload_size_mb * 1024 * 1024,
    }
    if body.filename:
        payload["filename"] = body.filename
    if body.content_type:
        payload["allow_mime_types"] = [body.content_type]

    client = request.app.state.http_client

    try:
        response = await client.post(
            PINATA_SIGN_URL,
            headers={"Authorization": f"Bearer {settings.pinata_jwt}"},
            json=payload,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Could not reach IPFS pinning service: {exc}"
        ) from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to create signed upload URL ({response.status_code}): {response.text}",
        )

    data = response.json()
    # Pinata's v3 API wraps most payloads in a "data" key; fall back to the
    # raw body in case that shape changes — worth re-checking against
    # current Pinata docs before relying on this in production.
    signed_url = data.get("data") if isinstance(data, dict) else data
    if not isinstance(signed_url, str):
        raise HTTPException(
            status_code=502,
            detail=f"Unexpected response shape from Pinata sign endpoint: {data}",
        )

    return SignedUrlResponse(url=signed_url, expires_in=SIGNED_URL_TTL_SECONDS)


@router.post("/upload", response_model=UploadResponse)
async def upload_model(request: Request, file: UploadFile = File(...)) -> UploadResponse:
    """
    Relay upload: file passes through this backend before reaching Pinata.
    Kept for small files (thumbnails, metadata JSON) where a second hop
    doesn't matter. For actual model weight files, prefer
    POST /upload/signed-url and have the client upload directly.
    """
    if not settings.pinata_jwt:
        raise HTTPException(
            status_code=500,
            detail="PINATA_JWT is not configured on the server",
        )

    size_bytes = await run_in_threadpool(_measure_and_rewind, file.file)

    if size_bytes == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds max upload size of {settings.max_upload_size_mb}MB",
        )

    client = request.app.state.http_client

    try:
        response = await client.post(
            PINATA_PIN_URL,
            headers={"Authorization": f"Bearer {settings.pinata_jwt}"},
            files={"file": (file.filename, file.file, file.content_type)},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Could not reach IPFS pinning service: {exc}"
        ) from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"IPFS pin failed ({response.status_code}): {response.text}",
        )

    data = response.json()
    cid = data["IpfsHash"]

    return UploadResponse(
        cid=cid,
        filename=file.filename or "unnamed",
        size_bytes=size_bytes,
        gateway_url=f"{settings.pinata_gateway}/{cid}",
    )