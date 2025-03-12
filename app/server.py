import asyncio
import os
import secrets
from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import messages
from app.config.roles import Role
from app.config.task_status import TaskStatus
from app.db.models import User
from app.db.requests import (
    get_factory,
    get_tasks,
    get_user,
    set_user,
    update_task,
    update_user,
)
from app.instances import ThreadSafeKey, TimerSingleton, bot, loop
from app.utils import setup_logger

server = FastAPI()

logger = setup_logger(__name__)


class AuthRequest(BaseModel):
    key: int


class GetTasks(BaseModel):
    token: int


class Object(BaseModel):
    name: str
    latitude: float
    longitude: float


class Task(BaseModel):
    id: int
    admin_id: int
    object: Object
    description: str
    created: datetime


class HandledTask(BaseModel):
    token: int
    id: int
    name: str
    admin_id: int
    status: TaskStatus
    note: Optional[str] = ""


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


@server.post("/get_current_tasks")
async def get_current_tasks(request: GetTasks):
    try:
        user = asyncio.run_coroutine_threadsafe(get_user(request.token), loop).result()
    except Exception:
        raise HTTPException(
            status_code=401, detail="Token has expired, please log in again"
        )
    if user.role != Role.WORKER:
        raise HTTPException(
            status_code=401, detail="Token has expired, please log in again"
        )
    tasks = asyncio.run_coroutine_threadsafe(
        get_tasks(user.id, TaskStatus.WAIT), loop
    ).result()
    res = []
    for task in tasks:
        object = asyncio.run_coroutine_threadsafe(
            get_factory(task.object_id), loop
        ).result()
        obj = Object(
            name=object.name, latitude=object.latitude, longitude=object.longitude
        )
        res.append(
            Task(
                id=task.id,
                admin_id=task.admin_id,
                object=obj,
                description=task.description,
                created=task.created,
            )
        )
    return res


@server.post("/update_assigned_task")
async def update_assigned_task(request: HandledTask):
    try:
        user = asyncio.run_coroutine_threadsafe(get_user(request.token), loop).result()
    except Exception:
        raise HTTPException(
            status_code=401, detail="Token has expired, please log in again"
        )
    if user.role != Role.WORKER:
        raise HTTPException(
            status_code=401, detail="Token has expired, please log in again"
        )
    try:
        task = asyncio.run_coroutine_threadsafe(
            update_task(request.id, request.status, request.note), loop
        ).result()
        admin = asyncio.run_coroutine_threadsafe(
            get_user(request.admin_id, False), loop
        ).result()
        if request.status == TaskStatus.COMPLETE:
            asyncio.run_coroutine_threadsafe(
                bot.send_message(
                    chat_id=admin.tg_id,
                    text=messages.SEND_COMPLETE_TASK.format(
                        request.name, user.fullname, task.description
                    ),
                ),
                loop,
            ).result()
        elif request.status == TaskStatus.CANCELED:
            asyncio.run_coroutine_threadsafe(
                bot.send_message(
                    chat_id=admin.tg_id,
                    text=messages.SEND_DENIED_TASK.format(
                        request.name, user.fullname, request.note, task.description
                    ),
                ),
                loop,
            ).result()
    except Exception:
        return HTTPException(status_code=500)
    else:
        return JSONResponse(status_code=200, content={"message": "OK"})
