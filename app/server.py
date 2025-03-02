import asyncio
import os
import secrets

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.instances import ThreadSafeKey, TimerSingleton, loop
from app.utils import setup_logger

server = FastAPI()

logger = setup_logger(__name__)


class AuthRequest(BaseModel):
    key: int
    name: str


def run_server():
    """Запуск веб-сервера."""
    logger.info("Запуск FastAPI сервера в новом потоке")
    uvicorn.run(server, host="0.0.0.0", port=int(os.getenv("SERVER_PORT")))


@server.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return None


@server.post("/auth")
async def authenticate(request: AuthRequest):
    if ThreadSafeKey.is_valid(request.key):
        asyncio.run_coroutine_threadsafe(TimerSingleton().stop(request.name), loop)
        print("OK")
        return {"token": secrets.token_hex(16)}
    else:
        print("FALSE")
        raise HTTPException(status_code=401, detail="Неверный ключ")
