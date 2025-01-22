from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import labels, messages
from app.config.roles import Role
from app.db.requests import set_user
from app.keyboards import ownerKb
from app.utils import setup_logger
from app.utils.isonwer import is_owner

logger = setup_logger(__name__)
user = Router()


@user.message(CommandStart())
@user.message(F.text == labels.INSTRUCTION_BUTTON)
async def cmd_start(message: Message, state: FSMContext):
    """/start. Запуск бота.

    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """
    logger.info(f"cmd_start (from_user={message.from_user.id})")
    await state.clear()
    user = await set_user(message.from_user.id)

    if is_owner(str(message.from_user.id)):
        user.role = Role.OWNER

    match user.role:
        case Role.WORKER:
            msg = await message.answer(text=messages.MASTER_INSTRUCTION)
            await message.bot.unpin_all_chat_messages(message.from_user.id)
            await message.bot.pin_chat_message(message.from_user.id, msg.message_id)
        case Role.OWNER:
            await message.answer(text=messages.OWNER_INSTRUCTION, reply_markup=ownerKb)


@user.message(Command("myid"))
async def show_id(message: Message, state: FSMContext):
    """Теневая команда для получения user_id в tg.

    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """
    logger.info(f"show_id (from_user={message.from_user.id})")
    await state.clear()
    await message.answer(messages.YOUR_ID.format(message.from_user.id))


@user.callback_query(F.data.startswith("close_kb"))
async def close_list(callback: CallbackQuery, state: FSMContext):
    logger.info(f"close_list (from_user={callback.from_user.id})")
    await state.clear()
    await callback.answer()
    if callback.data.count("_") == 2:
        await callback.bot.delete_message(
            chat_id=callback.from_user.id, message_id=int(callback.data.split("_")[-1])
        )
    await callback.message.delete()


@user.callback_query(F.data == "_")
async def button_stop(callback: CallbackQuery, state: FSMContext):
    logger.info(f"button_stop (from_user={callback.from_user.id})")
    await callback.answer()
