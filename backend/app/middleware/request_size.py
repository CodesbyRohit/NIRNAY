import json
from collections.abc import Awaitable, Callable
from typing import Any

from app.services.screenshot_analysis import MAX_SCREENSHOT_BYTES

ASGIReceive = Callable[[], Awaitable[dict[str, Any]]]
ASGISend = Callable[[dict[str, Any]], Awaitable[None]]
SCREENSHOT_MULTIPART_OVERHEAD_BYTES = 64 * 1024
MAX_SCREENSHOT_REQUEST_BYTES = (
    MAX_SCREENSHOT_BYTES + SCREENSHOT_MULTIPART_OVERHEAD_BYTES
)
_SCREENSHOT_PATH = "/api/v1/analyze/screenshot"


class _RequestBodyTooLarge(Exception):
    pass


class ScreenshotRequestSizeLimitMiddleware:
    """Bound screenshot request bodies before Starlette parses multipart uploads."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: ASGIReceive,
        send: ASGISend,
    ) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or scope["path"] != _SCREENSHOT_PATH
        ):
            await self.app(scope, receive, send)
            return

        content_lengths = [
            value.strip()
            for name, value in scope.get("headers", [])
            if name.lower() == b"content-length"
        ]
        if content_lengths:
            if len(set(content_lengths)) != 1 or not content_lengths[0].isdigit():
                await self._send_error(send, 400, "Invalid Content-Length header.")
                return
            if int(content_lengths[0]) > MAX_SCREENSHOT_REQUEST_BYTES:
                await self._send_error(
                    send,
                    413,
                    "Screenshot request exceeds the allowed upload size.",
                )
                return

        received_bytes = 0
        response_started = False

        async def limited_receive() -> dict[str, Any]:
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > MAX_SCREENSHOT_REQUEST_BYTES:
                    raise _RequestBodyTooLarge
            return message

        async def tracked_send(message: dict[str, Any]) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except _RequestBodyTooLarge:
            if response_started:
                raise
            await self._send_error(
                send,
                413,
                "Screenshot request exceeds the allowed upload size.",
            )

    @staticmethod
    async def _send_error(send: ASGISend, status_code: int, detail: str) -> None:
        body = json.dumps({"detail": detail}).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
