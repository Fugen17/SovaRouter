from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove, TelegramObject

from app import keyboards as kb
from app.config import labels, messages
from app.config.db import ObjectLen, UserLen, WorkerTaskLen
from app.config.roles import Role
from app.db import requests
from app.db.exceptions import AlreadyExistsError, BadKeyError
from app.db.models import User
from app.db.requests import update_user
from app.filters import RoleFilter
from app.states import AddTask, PickAdmin, PickObject
from app.utils import setup_logger
from app.utils.isonwer import is_owner

logger = setup_logger(__name__)

owner = Router()  # Создаем экземпляр Router

owner.message.filter(RoleFilter(Role.OWNER))


@owner.message(F.text == labels.EDITING)
async def editing_menu(message: Message, state: FSMContext):
    logger.info(f"editing_menu (from_user={message.from_user.id})")
    await state.clear()
    await message.reply(text=messages.EDITING_MENU, reply_markup=kb.ownerEditingKb)


@owner.message(F.text == labels.MAIN_MENU)
async def back_main_menu(message: Message, state: FSMContext):
    logger.info(f"back_main_menu (from_user={message.from_user.id})")
    await state.clear()
    await message.reply(text=messages.RETURN_TO_MAIN_MENU, reply_markup=kb.ownerKb)


@owner.message(F.text == labels.ADD_TASK)
async def add_task(message: Message, state: FSMContext):
    logger.info(f"add_task (from_user={message.from_user.id})")
    await state.clear()
    reply_markup = await kb.get_list_by_role(Role.WORKER, 1, "task_")
    if not reply_markup:
        logger.debug("Список пуст")
        await message.answer(labels.NO_WORKERS, show_alert=True)
        return
    await state.set_state(AddTask.user_id)
    await message.reply(text=messages.CHOOSE_WORKER, reply_markup=reply_markup)


@owner.callback_query(F.data.startswith(f"task_{Role.WORKER}_"), AddTask.user_id)
async def get_user_task(callback: CallbackQuery, state: FSMContext):
    logger.info(f"get_user_task (from_user={callback.from_user.id})")
    id = int(callback.data.split("_")[2])
    await state.update_data(user_id=int(id))
    await state.set_state(AddTask.object_id)
    reply_markup = await kb.get_factory_page(1, "task_")

    if not reply_markup:
        logger.debug("Список пуст")
        await callback.answer(labels.NO_FACTORIES, show_alert=True)
        await state.clear()
        return
    await callback.message.edit_text(
        text=messages.CHOOSE_FACTORY_FOR_MASTER, reply_markup=reply_markup
    )


@owner.callback_query(F.data.startswith("task_factory_"), AddTask.object_id)
async def get_object_task(callback: CallbackQuery, state: FSMContext):
    logger.info(f"get_object_task (from_user={callback.from_user.id})")
    id = int(callback.data.split("_")[2])
    await state.update_data(object_id=int(id))
    await state.set_state(AddTask.description)
    await callback.message.edit_text(
        text=messages.ENTER_ACTIVITY_DURATION, reply_markup=kb.cancelKb
    )


@owner.message(AddTask.description)
async def get_description_task(message: Message, state: FSMContext):
    logger.info(f"get_description_task (from_user={message.from_user.id})")
    await state.update_data(description=message.text[: WorkerTaskLen.description])
    data = await state.get_data()
    await state.clear()
    await message.answer(text=messages.CONFIRM_CHANGE_JOB, reply_markup=None)
    user = await requests.get_user(data.get("user_id"), False)
    admin = await requests.get_user(message.from_user.id)
    object = await requests.get_factory(data.get("object_id"))
    task = await requests.add_task(admin.id, user.id, object.id, data.get("description"))
    msg = await message.bot.send_message(
        chat_id=user.tg_id,
        text=messages.WORKER_NUMBER,
    )
    await message.bot.send_location(
        chat_id=user.tg_id,
        latitude=object.latitude,
        longitude=object.longitude,
        reply_markup=await kb.get_task_kb(task.id, msg.message_id),
    )


# Управление админами
@owner.message(F.text == labels.WORKER_MANAGE)
@owner.callback_query(F.data == f"return_manage_{Role.WORKER}")
async def editing_admins(event: TelegramObject, state: FSMContext):
    logger.info(f"editing_admins (from_user={event.from_user.id})")
    await state.clear()
    # Если событие - это callback_query, то вызываем answer()
    if isinstance(event, CallbackQuery):
        await event.answer()

        await event.message.edit_text(text=messages.CHOOSE_OPTION, reply_markup=kb.adminManageKb)
    else:
        await event.reply(text=messages.CHOOSE_OPTION, reply_markup=kb.adminManageKb)


@owner.callback_query(F.data == "add_admin")
async def add_admin_id(callback: CallbackQuery, state: FSMContext):
    logger.info(f"add_admin_id (from_user={callback.from_user.id})")
    await state.clear()
    await state.set_state(PickAdmin.id)
    await callback.answer()
    await callback.message.edit_text(text=messages.ADMIN_ADD_TEXT, reply_markup=None)
    await callback.message.answer(text=messages.ENTER_ADMIN_ID)


@owner.message(PickAdmin.id)
async def add_admin_name(message: Message, state: FSMContext):
    logger.info(f"add_admin_name (from_user={message.from_user.id})")
    await state.update_data(id=message.text)
    await state.set_state(PickAdmin.name)
    await message.answer(text=messages.ENTER_ADMIN_NAME)


@owner.message(PickAdmin.name)
async def admin_add_confirm(message: Message, state: FSMContext):
    logger.info(f"admin_add_confirm (from_user={message.from_user.id})")
    admin_name = message.text[: UserLen.fullname]
    await state.update_data(name=admin_name)
    try:
        data = await state.get_data()
        user_info = await message.bot.get_chat(data.get("id"))
        await message.answer(
            text=messages.ADMIN_ADD_CONF.format(user_info.username, data.get("name")),
            reply_markup=kb.confirmAdminAdd,
        )
    except TelegramBadRequest:
        logger.debug("tg id не существует")
        await message.answer(text=messages.TG_ID_NOT_EXIST, reply_markup=kb.ownerEditingKb)
        await state.clear()
    except Exception as ex:
        logger.error(f"Ошибка добавления админа:\n{ex}")


@owner.callback_query(F.data == "add_admin_denied", PickAdmin.name)
async def add_admin_denied(callback: CallbackQuery, state: FSMContext):
    logger.info(f"add_admin_denied (from_user={callback.from_user.id})")
    await state.clear()
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(text=messages.CANCEL_ADD, reply_markup=kb.ownerEditingKb)


@owner.callback_query(F.data == "add_admin_confirm", PickAdmin.name)
async def add_admin_confirm(callback: CallbackQuery, state: FSMContext):
    logger.info(f"add_admin_confirm (from_user={callback.from_user.id})")
    data = await state.get_data()
    try:
        tg_id = int(data.get("id"))
        potential_worker = await requests.get_user(tg_id)
        if (potential_worker.role >= Role.WORKER) or is_owner(str(tg_id)):
            logger.debug("Роль юзера >= worker")
            await callback.message.answer(text=messages.INCORRECT_TG_ID)
            return
        await update_user(tg_id, {User.fullname: data.get("name"), User.role: Role.WORKER})
        await callback.message.answer(text=messages.CONFIRM_ADD, reply_markup=kb.ownerEditingKb)

        await callback.message.bot.send_message(
            chat_id=data.get("id"),
            text=messages.GIVE_ADMIN_ROLE.format(data.get("name")),
            reply_markup=kb.workerKb,
        )
    except BadKeyError:
        logger.debug("Юзер не нажимал /start")
        await callback.message.answer(text=messages.DOESNT_EXIST, reply_markup=kb.ownerEditingKb)
    except Exception as ex:
        logger.error(f"Невохможно добавить админа:\n{ex}")
    finally:
        await state.clear()
        await callback.answer()
        await callback.message.edit_reply_markup(reply_markup=None)


@owner.callback_query(F.data == "list_admins")
async def admin_list(callback: CallbackQuery, state: FSMContext):
    logger.info(f"admin_list (from_user={callback.from_user.id})")
    reply_markup = await kb.get_list_by_role(Role.WORKER, 1)
    if not reply_markup:
        logger.debug("Список пуст")
        await callback.answer(labels.EMPTY_LIST, show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(text=labels.ADMIN_LIST, reply_markup=reply_markup)


@owner.callback_query(F.data.startswith(f"page_{Role.WORKER}_"))
@owner.callback_query(F.data.startswith(f"task_page_{Role.WORKER}_"), AddTask.user_id)
async def show_admin_list_page(callback: CallbackQuery, state: FSMContext):
    logger.info(f"show_admin_list_page (from_user={callback.from_user.id})")
    key = "task_" if callback.data.split("_")[0] == "task" else ""
    reply_markup = await kb.get_list_by_role(Role.WORKER, int(callback.data.split("_")[-1]), key)
    if not reply_markup:
        logger.debug("Список пуст")
        await callback.answer(labels.EMPTY_LIST, show_alert=True)
        return
    await callback.answer()
    if key == "task_":
        await callback.message.edit_text(text=messages.CHOOSE_WORKER, reply_markup=reply_markup)
    else:
        await callback.message.edit_text(text=labels.ADMIN_LIST, reply_markup=reply_markup)


@owner.callback_query(F.data.startswith(f"{Role.WORKER}_"))
async def admin_info(callback: CallbackQuery, state: FSMContext):
    logger.info(f"admin_info (from_user={callback.from_user.id})")
    await callback.answer()
    id = int(callback.data.split("_")[1])
    page = int(callback.data.split("_")[2])

    user = await requests.get_user(id, use_tg=False)
    user_tg_info = await callback.bot.get_chat(user.tg_id)
    await callback.message.edit_text(
        text=messages.ADMIN_INFO.format(user.fullname, user_tg_info.username),
        reply_markup=await kb.manage_people(Role.WORKER, user_tg_id=user.tg_id, back_page=page),
    )


@owner.callback_query(F.data.startswith(f"dismiss_{Role.WORKER}_"))
async def dismiss_admin(callback: CallbackQuery, state: FSMContext):
    logger.info(f"dismiss_admin (from_user={callback.from_user.id})")
    await callback.answer()
    user_tg_id = int(callback.data.split("_")[2])

    user = await requests.get_user(user_tg_id)
    user_tg_info = await callback.bot.get_chat(user_tg_id)
    await callback.message.edit_text(
        text=messages.DELETE_ADMIN.format(user.fullname, user_tg_info.username),
        reply_markup=await kb.person_delete(Role.WORKER, user_tg_id),
    )


@owner.callback_query(F.data.startswith("confirm_dismiss_"))
async def confirm_dismiss_admin(callback: CallbackQuery, state: FSMContext):
    logger.info(f"confirm_dismiss_admin (from_user={callback.from_user.id})")
    await callback.answer()
    user_tg_id = int(callback.data.split("_")[3])

    await requests.update_user(user_tg_id, {User.role: Role.USER})
    try:
        await callback.message.edit_text(text=messages.ADMIN_DELETED, reply_markup=None)
        await callback.bot.send_message(
            chat_id=user_tg_id, text=messages.YOU_DISMISSED, reply_markup=ReplyKeyboardRemove()
        )
    except Exception as ex:
        logger.error(f"confirm_dismiss\n{ex}")


@owner.callback_query(F.data.startswith("denied_dismiss_"))
async def denied_dismiss(callback: CallbackQuery, state: FSMContext):
    logger.info(f"denied_dismiss (from_user={callback.from_user.id})")
    await callback.answer()
    await callback.message.edit_text(text=messages.DISMISS_DENIED, reply_markup=None)
    if callback.data.split("_")[2] == "factory":
        await callback.bot.delete_message(
            chat_id=callback.from_user.id, message_id=int(callback.data.split("_")[-1])
        )


@owner.message(F.text == labels.OBJECTS_MANAGE)
@owner.callback_query(F.data == "return_factories")
async def objects_manage(event: TelegramObject, state: FSMContext):
    logger.info(f"objects_manage (from_user={event.from_user.id})")
    await state.clear()
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.edit_text(text=messages.CHOOSE_OPTION, reply_markup=kb.objects_manage)
    else:
        await event.reply(text=messages.CHOOSE_OPTION, reply_markup=kb.objects_manage)


@owner.callback_query(F.data == "add_factory")
async def add_factory_company(callback: CallbackQuery, state: FSMContext):
    logger.info(f"add_factory_company (from_user={callback.from_user.id})")
    await callback.answer()
    await state.set_state(PickObject.name)
    await callback.message.edit_text(text=messages.FACTORY_ADD_TEXT, reply_markup=None)
    await callback.message.answer(text=messages.ENTER_COMPANY_NAME)


@owner.message(PickObject.name)
async def add_factory_name(message: Message, state: FSMContext):
    logger.info(f"add_factory_name (from_user={message.from_user.id})")
    name = message.text[: ObjectLen.name]
    await state.update_data(name=name)
    await state.set_state(PickObject.description)
    await message.answer(text=messages.ENTER_FACTORY_NAME)


@owner.message(PickObject.description)
async def add_factory_description(message: Message, state: FSMContext):
    logger.info(f"add_factory_description (from_user={message.from_user.id})")
    description = message.text[: ObjectLen.description]
    await state.update_data(description=description)
    await state.set_state(PickObject.location)
    await message.answer(text=messages.ENTER_FACTORY_LOCATION)


@owner.message(PickObject.location)
async def add_factory_confirm(message: Message, state: FSMContext):
    logger.info(f"add_factory_confirm (from_user={message.from_user.id})")
    if not message.location:
        await message.answer(text=messages.NOT_LOCATION, reply_markup=kb.cancelObjectKb)
        return
    await state.update_data(location=(message.location.latitude, message.location.longitude))

    data = await state.get_data()
    await message.answer(
        text=messages.FACTORY_ADD_CONFIRM.format(
            data.get("name"), data.get("description"), data.get("location")
        ),
        reply_markup=kb.confirm_factory_add,
    )


@owner.callback_query(F.data == "add_denied")
async def add_denied(callback: CallbackQuery, state: FSMContext):
    logger.info(f"add_denied (from_user={callback.from_user.id})")
    await state.clear()
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(text=messages.CANCEL_ADD)


@owner.callback_query(F.data == "add_factory_confirm")
async def add_factory(callback: CallbackQuery, state: FSMContext):
    logger.info(f"add_factory (from_user={callback.from_user.id})")
    await callback.answer()

    data = await state.get_data()
    try:
        await requests.set_factory(data.get("name"), data.get("description"), data.get("location"))
        await callback.message.answer(text=messages.CONFIRM_ADD, reply_markup=None)
    except AlreadyExistsError:
        logger.debug("Предприятие уже существует")
        await callback.message.answer(text=messages.ALREADY_EXISTS_FACTORY, reply_markup=None)
    finally:
        await callback.message.edit_reply_markup(reply_markup=None)
        await state.clear()


# Список заводов
@owner.callback_query(F.data.startswith("factory_list"))
async def factory_list(callback: CallbackQuery, state: FSMContext):
    logger.info(f"factory_list (from_user={callback.from_user.id})")
    if callback.data.count("_") == 2:
        await callback.bot.delete_message(
            chat_id=callback.from_user.id, message_id=int(callback.data.split("_")[-1])
        )
    reply_markup = await kb.get_factory_page(1)

    if not reply_markup:
        logger.debug("Список пуст")
        await callback.answer(labels.EMPTY_LIST, show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(text=labels.FACTORY_LIST, reply_markup=reply_markup)


@owner.callback_query(F.data.startswith("page_factory_"))
@owner.callback_query(F.data.startswith("task_page_factory_"), AddTask.object_id)
async def show_factory_list_page(callback: CallbackQuery, state: FSMContext):
    logger.info(f"show_admin_list_page (from_user={callback.from_user.id})")
    key = "task_" if callback.data.split("_")[0] == "task" else ""
    reply_markup = await kb.get_factory_page(int(callback.data.split("_")[-1]), key)
    if not reply_markup:
        logger.debug("Список пуст")
        await callback.answer(labels.EMPTY_LIST, show_alert=True)
        return
    await callback.answer()
    if key == "task_":
        await callback.message.edit_text(
            text=messages.CHOOSE_FACTORY_FOR_MASTER, reply_markup=reply_markup
        )
    else:
        await callback.message.edit_text(text=labels.FACTORY_LIST, reply_markup=reply_markup)


@owner.callback_query(F.data.startswith("factory_"))
async def factory_info(callback: CallbackQuery, state: FSMContext):
    logger.info(f"factory_info (from_user={callback.from_user.id})")
    await callback.answer()
    fact_id = int(callback.data.split("_")[1])
    factory = await requests.get_factory(fact_id)
    msg_location_id = await callback.bot.send_location(
        chat_id=callback.from_user.id, latitude=factory.latitude, longitude=factory.longitude
    )
    await callback.message.edit_text(
        text=messages.FACTORY_INFO.format(factory.name, factory.description),
        reply_markup=await kb.manage_object(fact_id, msg_location_id.message_id),
    )


@owner.callback_query(F.data.startswith("delete_factory_"))
async def delete_factory(callback: CallbackQuery, state: FSMContext):
    logger.info(f"delete_factory (from_user={callback.from_user.id})")
    await callback.answer()
    fact_id = int(callback.data.split("_")[2])
    msg_id = int(callback.data.split("_")[3])
    factory = await requests.get_factory(fact_id)
    await callback.message.edit_text(
        text=messages.CONFIRM_DELETE_FACT.format(factory.name),
        reply_markup=await kb.confirm_delete_fact(fact_id, msg_id),
    )


@owner.callback_query(F.data.startswith("confirm_delete_factory_"))
async def confirm_delete_fact(callback: CallbackQuery, state: FSMContext):
    logger.info(f"confirm_delete_fact (from_user={callback.from_user.id})")
    await callback.answer()
    fact_id = int(callback.data.split("_")[3])
    msg_id = int(callback.data.split("_")[4])
    await callback.bot.delete_message(chat_id=callback.from_user.id, message_id=msg_id)
    await requests.delete_factory(fact_id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(text=messages.FACTORY_DELETED)
