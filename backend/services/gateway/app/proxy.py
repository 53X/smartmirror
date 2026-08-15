"""HTTP forwarding helpers. Image bodies are not written to logs."""

from __future__ import annotations

from collections.abc import Mapping

import httpx
from fastapi import HTTPException, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from smartmirror_shared.logging_config import configure_service_logging

from app.settings import settings

logger = configure_service_logging("gateway", settings.log_level)


async def proxy_json(
    method: str,
    base_url: str,
    path: str,
    request: Request | None = None,
    json_body: Mapping[str, object] | None = None,
    params: Mapping[str, object] | None = None,
) -> Response:
    """Forward a JSON API call to catalog or AI service."""
    url = f"{base_url.rstrip('/')}{path}"
    logger.info("proxy %s %s", method, path)
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.request(
                method,
                url,
                json=json_body,
                params=params,
                headers=_forward_headers(request),
            )
    except httpx.ConnectError as exc:
        logger.warning("upstream_unreachable %s", path)
        raise HTTPException(status_code=502, detail="Upstream service unreachable") from exc
    return _as_response(response)


async def proxy_multipart(
    base_url: str,
    path: str,
    data: dict[str, str | list[str]],
    files: list[tuple[str, tuple[str, bytes, str]]],
) -> Response:
    """Forward multipart uploads without logging file bytes."""
    url = f"{base_url.rstrip('/')}{path}"
    logger.info("proxy_multipart POST %s files=%s", path, len(files))
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(url, data=data, files=files)
    return _as_response(response)


async def proxy_stream(base_url: str, path: str) -> StreamingResponse:
    """Stream media so the kiosk can show stills without buffering in the BFF log."""
    url = f"{base_url.rstrip('/')}{path}"
    client = httpx.AsyncClient(timeout=60)
    request = client.build_request("GET", url)
    response = await client.send(request, stream=True)
    if response.status_code >= 400:
        await response.aclose()
        await client.aclose()
        raise HTTPException(status_code=response.status_code, detail="Upstream media error")

    async def iterator():
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return StreamingResponse(
        iterator(),
        media_type=response.headers.get("content-type", "application/octet-stream"),
    )


async def read_upload(upload: UploadFile) -> tuple[str, bytes, str]:
    """Read an upload into memory for a single downstream hop."""
    payload = await upload.read()
    filename = upload.filename or "upload.bin"
    content_type = upload.content_type or "application/octet-stream"
    return filename, payload, content_type


def _forward_headers(request: Request | None) -> dict[str, str]:
    if request is None:
        return {}
    headers: dict[str, str] = {}
    request_id = request.headers.get("x-request-id")
    if request_id:
        headers["x-request-id"] = request_id
    return headers


def _as_response(response: httpx.Response) -> Response:
    excluded = {"content-encoding", "content-length", "transfer-encoding", "connection"}
    headers = {key: value for key, value in response.headers.items() if key.lower() not in excluded}
    return Response(content=response.content, status_code=response.status_code, headers=headers)
