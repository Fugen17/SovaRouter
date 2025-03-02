import asyncio
import os
import secrets

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.config.roles import Role
from app.db.models import User
from app.db.requests import get_user, set_user, update_user
from app.instances import ThreadSafeKey, TimerSingleton, loop
from app.utils import setup_logger

server = FastAPI()

logger = setup_logger(__name__)


class AuthRequest(BaseModel):
    key: int


class GetRequest(BaseModel):
    token: int


def run_server():
    """Запуск веб-сервера."""
    logger.info("Запуск FastAPI сервера в новом потоке")
    uvicorn.run(server, host="0.0.0.0", port=int(os.getenv("SERVER_PORT")))


@server.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return None


@server.post("/auth")
async def authenticate(request: AuthRequest):
    if name := ThreadSafeKey.is_valid(request.key):
        user = asyncio.run_coroutine_threadsafe(set_user(), loop).result()
        token = secrets.randbits(63)
        asyncio.run_coroutine_threadsafe(
            update_user(
                user.id,
                {User.tg_id: token, User.fullname: name, User.role: Role.WORKER},
                False,
            ),
            loop,
        ).result()
        asyncio.run_coroutine_threadsafe(TimerSingleton().stop(name), loop)
        return {"token": token}
    else:
        logger.debug("Key is wrong")
        raise HTTPException(status_code=401, detail="Token is invalid")


@server.get("/objects")
async def get_tasks(request: GetRequest):
    user = asyncio.run_coroutine_threadsafe(get_user(request.token), loop).result()
    if user.role != Role.WORKER:
        raise HTTPException(
            status_code=401, detail="Token has expired, please log in again"
        )
    return {"data": "ok"}
