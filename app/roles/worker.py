from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app import keyboards as kb
from app.config import messages
from app.config.db import WorkerTaskLen
from app.config.roles import Role
from app.config.task_status import TaskStatus
from app.db import requests
from app.filters import RoleFilter
from app.states import TaskReport
from app.utils import setup_logger

logger = setup_logger(__name__)
worker = Router()

worker.message.filter(RoleFilter(Role.WORKER))


@worker.callback_query(F.data.startswith("mytask_back_"))
async def task_back(callback: CallbackQuery, state: FSMContext):
    logger.info(f"task_back (from_user={callback.from_user.id})")
    await callback.answer()
    task_id = int(callback.data.split("_")[-1])
    task = await requests.get_task(task_id)
    object = await requests.get_factory(task.object_id)
    await callback.message.edit_text(
        text=messages.ASSIGN_TASK.format(object.name, task.description)
    )
    await callback.message.answer_location(
        latitude=object.latitude,
        longitude=object.longitude,
        reply_markup=await kb.get_task_kb(task_id, callback.message.message_id),
    )


@worker.callback_query(F.data.startswith("mytask_"))
async def task(callback: CallbackQuery, state: FSMContext):
    logger.info(f"task (from_user={callback.from_user.id})")
    await callback.answer()
    task_id = int(callback.data.split("_")[-2])
    msg_id = int(callback.data.split("_")[-1])
    if callback.data.split("_")[1] == "complete":
        task = await requests.update_task(task_id, TaskStatus.COMPLETE)
        user = await requests.get_user(task.admin_id, False)
        object = await requests.get_factory(task.object_id)
        await callback.bot.send_message(
            chat_id=user.tg_id,
            text=messages.SEND_COMPLETE_TASK.format(object.name, user.fullname, task.description),
        )
        await callback.bot.delete_message(
            chat_id=callback.from_user.id, message_id=callback.message.message_id
        )
        await callback.bot.edit_message_text(
            chat_id=callback.from_user.id,
            message_id=msg_id,
            text=messages.EDIT_COMPLETE_TASK.format(object.name, task.description),
            reply_markup=None,
        )
    else:
        await state.clear()
        await state.set_state(TaskReport.msg_id)
        await state.update_data(msg_id=msg_id)
        await state.set_state(TaskReport.id)
        await state.update_data(id=task_id)
        await callback.bot.edit_message_text(
            chat_id=callback.from_user.id,
            message_id=msg_id,
            text=messages.TASK_REASON,
            reply_markup=await kb.task_back_kb(task_id),
        )
        await callback.bot.delete_message(
            chat_id=callback.from_user.id, message_id=callback.message.message_id
        )


@worker.message(TaskReport.id)
async def deny_task(message: Message, state: FSMContext):
    logger.info(f"deny_task (from_user={message.from_user.id})")
    data = await state.get_data()
    await state.clear()
    reason = message.text[: WorkerTaskLen.note]
    task = await requests.update_task(data.get("id"), TaskStatus.CANCELED, reason)
    admin = await requests.get_user(task.admin_id, False)
    object = await requests.get_factory(task.object_id)
    await message.bot.delete_message(chat_id=message.from_user.id, message_id=message.message_id)
    await message.bot.edit_message_text(
        chat_id=message.from_user.id,
        message_id=data.get("msg_id"),
        text=messages.EDIT_DENIED_TASK.format(object.name, reason, task.description),
        reply_markup=None,
    )
    user = await requests.get_user(message.from_user.id)
    await message.bot.send_message(
        chat_id=admin.tg_id,
        text=messages.SEND_DENIED_TASK.format(
            object.name, user.fullname, reason, task.description
        ),
    )
