"""Response policy for Dataset share routes, including rejected requests."""

import re

from starlette.datastructures import MutableHeaders

PUBLIC_DATASET_VIEW = "/api/public/v1/dataset-view"
DATASET_SHARE_HEADER = "X-Dataset-Share"
SHARE_MANAGEMENT = re.compile(r"^/api/datasets/[^/]+/shares(?:/.*)?$")


def share_response_headers(path: str) -> dict[str, str]:
    if path == PUBLIC_DATASET_VIEW or path.startswith(PUBLIC_DATASET_VIEW + "/"):
        return {"Cache-Control": "no-store", "X-Robots-Tag": "noindex", "Referrer-Policy": "no-referrer"}
    return {"Cache-Control": "no-store"} if SHARE_MANAGEMENT.fullmatch(path) else {}


class DatasetShareHeaders:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        policy = share_response_headers(scope.get("path", "")) if scope["type"] == "http" else {}
        if not policy:
            return await self.app(scope, receive, send)

        async def apply_headers(message):
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).update(policy)
            await send(message)

        return await self.app(scope, receive, apply_headers)
