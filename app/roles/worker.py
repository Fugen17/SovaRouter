from datetime import date, datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject

from app import keyboards as kb
from app.config import labels, messages
from app.config.roles import Role
from app.config.task_status import TaskStatus
from app.db import requests
from app.filters import RoleFilter
from app.states import TaskReport
from app.utils import setup_logger

logger = setup_logger(__name__)
worker = Router()

worker.message.filter(RoleFilter(Role.WORKER))


@worker.callback_query(F.data.startwith == "task_")
async def task(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[-1])
    if callback.data.split("_")[1] == "complete":
        task = await requests.update_task(task_id, TaskStatus.COMPLETE)
        object = await requests.get_factory(task.object_id)
        await callback.bot.send_message(
            chat_id=task.admin_id, text=object.name + " " + task.description
        )
    else:
        await state.clear()
        await state.set_data(TaskReport.id)
        await state.update_data(id=task_id)
        await callback.message.edit_text(
            text=messages.ACTIVITY_CODES, reply_markup=kb.task_back_kb(task_id)
        )


@worker.message(TaskReport.id)
async def deny_task(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    reason = message.text
    task = await requests.update_task(data.get("id"), TaskStatus.CANCELED, reason)
    object = await requests.get_factory(task.object_id)
    await message.bot.send_message(
        chat_id=task.admin_id, text=object.name + " " + task.description + " " + reason
    )
