"""Bounded multipart inference route, separated from model execution."""
import logging
import os
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from ml.preprocessing.image_input import decode_image, MAX_IMAGE_BYTES
from ml.inference import multimodal

router = APIRouter()
logger = logging.getLogger(__name__)


def image_upload_limit():
    # Leave multipart headroom beneath the Vercel 4.5 MB request-body cap.
    return 4 * 1024 * 1024 if os.environ.get("VERCEL") == "1" else MAX_IMAGE_BYTES


class UploadBodyLimit:
    """Bound raw multipart bytes before parsing, including chunked requests."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] != "/api/predict/multimodal":
            return await self.app(scope, receive, send)
        limit = image_upload_limit() + 128 * 1024
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > limit:
                return await JSONResponse({"detail": "Upload exceeds the inference request limit."}, status_code=413)(scope, receive, send)
            if not message.get("more_body"):
                break
        sent = False

        async def buffered_receive():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, buffered_receive, send)


@router.post("/api/predict/multimodal")
async def predict_multimodal(text: str = Form(..., min_length=1, max_length=10000), image: UploadFile = File(...)):
    try:
        text = text.strip()
        if not text:
            raise HTTPException(422, "Enter a headline or article.")
        if image.content_type and not image.content_type.startswith("image/") and image.content_type != "application/octet-stream":
            raise HTTPException(415, "Choose an image for multimodal inference.")
        data = await image.read(image_upload_limit() + 1)
        if len(data) > image_upload_limit():
            raise HTTPException(413, f"Image exceeds the {image_upload_limit() // 1024 // 1024} MB inference limit.")
        try:
            decoded = await run_in_threadpool(decode_image, data)
        except ValueError as error:
            raise HTTPException(415, str(error)) from error
        try:
            readiness = await run_in_threadpool(multimodal.status)
            if not readiness["available"]:
                raise HTTPException(503, f"Multimodal classifier unavailable: {readiness['status']}. Install a trained checkpoint and matching local encoder.")
            try:
                return await run_in_threadpool(multimodal.predict_pair, text, decoded)
            except Exception as error:
                logger.exception("Multimodal inference failed")
                raise HTTPException(503, "Multimodal inference failed. Check checkpoint compatibility in server logs.") from error
        finally:
            decoded.close()
    finally:
        await image.close()
