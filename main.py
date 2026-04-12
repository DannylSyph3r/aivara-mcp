import logging
import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _log_level, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mcp_instance import mcp

_AIVARA_API_KEY = os.getenv("AIVARA_API_KEY")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("aivara_mcp_startup log_level=%s", _log_level)
    async with mcp.session_manager.run():
        yield
    logger.info("aivara_mcp_shutdown")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    api_key = request.headers.get("X-Aivara-Key")

    if not api_key:
        logger.warning(
            "security_rejected_missing_key path=%s method=%s",
            request.url.path, request.method,
        )
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized", "detail": "X-Aivara-Key header is required"},
        )

    if api_key != _AIVARA_API_KEY:
        logger.warning(
            "security_rejected_invalid_key path=%s method=%s key_prefix=%s",
            request.url.path, request.method, api_key[:6],
        )
        return JSONResponse(
            status_code=403,
            content={"error": "Forbidden", "detail": "Invalid API key"},
        )

    logger.info(
        "security_authorized path=%s method=%s",
        request.url.path, request.method,
    )
    return await call_next(request)


app.mount("/", mcp.streamable_http_app())