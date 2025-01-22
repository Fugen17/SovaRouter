from datetime import date
from math import ceil

from aiogram import Bot
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import labels
from app.config.keyboards import KEYBOARD_PAGE_SIZE
from app.config.roles import Role
from app.db import requests
from app.utils import setup_logger

logger = setup_logger(__name__)

ownerEditingKb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=labels.WORKER_MANAGE)],
        [KeyboardButton(text=labels.OBJECTS_MANAGE)],
        [KeyboardButton(text=labels.MAIN_MENU)],
    ],
    resize_keyboard=True,
)

ownerKb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=labels.EDITING)],
        [KeyboardButton(text=labels.ADD_TASK)],
        [KeyboardButton(text=labels.INSTRUCTION_BUTTON)],
    ],
    resize_keyboard=True,
)

workerKb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=labels.GET_TASKS)],
        [KeyboardButton(text=labels.INSTRUCTION_BUTTON)],
    ],
    resize_keyboard=True,
)


adminManageKb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=labels.ADD_ADMIN, callback_data="add_admin")],
        [InlineKeyboardButton(text=labels.ADMIN_LIST, callback_data="list_admins")],
        [InlineKeyboardButton(text=labels.CLOSE, callback_data="close_kb")],
    ]
)

confirmAdminAdd = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=labels.YES, callback_data="add_admin_confirm"),
            InlineKeyboardButton(text=labels.NO, callback_data="add_admin_denied"),
        ],
        [InlineKeyboardButton(text=labels.CLOSE, callback_data="close_kb")],
    ]
)

cancelObjectKb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=labels.CANCEL_EDITING, callback_data="return_factories")]
    ]
)

cancelKb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text=labels.CANCEL_EDITING, callback_data="close_kb")]]
)


async def get_task_kb(task_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=labels.WRITE_SHIFT, callback_data=f"task_complete_{task_id}"
                ),
                InlineKeyboardButton(
                    text=labels.DENIE_SHIFT, callback_data=f"task_denie_{task_id}"
                ),
            ]
        ]
    )


async def task_back_kb(task_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=labels.RETURN, callback_data=f"task_{task_id}"),
            ]
        ]
    )


async def get_list_by_role(role: Role, cur_page: int, key: str = "", end: str = ""):
    """Универсальная клавиатура.

    Code:
        "admin" - admin list
        "master" - master list
        "worker" - worker list for admin
        "mworkers" - workerlist for master

    Returns:
        InlineKeyboardMarkup: Inline кнопки.
    """
    people_list = await requests.get_users_by_role(role)

    if not people_list:
        return None

    pages_num = ceil(len(people_list) / KEYBOARD_PAGE_SIZE)
    from_i = KEYBOARD_PAGE_SIZE * (cur_page - 1)
    to_i = min(len(people_list), KEYBOARD_PAGE_SIZE * cur_page)
    keyboard = InlineKeyboardBuilder()

    for i in range(from_i, to_i):
        logger.debug(f"{key}{role}_{people_list[i].id}_{cur_page}")
        keyboard.row(
            InlineKeyboardButton(
                text=people_list[i].fullname,
                callback_data=f"{key}{role}_{people_list[i].id}_{cur_page}{end}",
            ),
        )

    keyboard.row(
        InlineKeyboardButton(
            text=labels.BACK,
            callback_data=(f"{key}page_{role}_{cur_page - 1}{end}" if cur_page - 1 > 0 else "_"),
        ),
        InlineKeyboardButton(text=f"{cur_page}/{pages_num}", callback_data="_"),
        InlineKeyboardButton(
            text=labels.FORWARD,
            callback_data=(
                f"{key}page_{role}_{cur_page + 1}{end}" if cur_page < pages_num else "_"
            ),
        ),
    )

    logger.debug(f"{key}return_manage_{role}")
    if key == "task_":
        keyboard.row(
            InlineKeyboardButton(text=labels.CANCEL_EDITING, callback_data="close_kb"),
        )
    else:
        keyboard.row(
            InlineKeyboardButton(
                text=labels.RETURN, callback_data=f"{key}return_manage_{role}{end}"
            ),
            InlineKeyboardButton(text=labels.CLOSE, callback_data="close_kb"),
        )

    return keyboard.as_markup()


async def manage_people(role: Role, user_tg_id: int, back_page: int):
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        InlineKeyboardButton(text=labels.DISMISS, callback_data=f"dismiss_{role}_{user_tg_id}")
    )

    # через if добавить кнопки для мастеров и работников

    keyboard.row(
        InlineKeyboardButton(text=labels.RETURN, callback_data=f"page_{role}_{back_page}"),
        InlineKeyboardButton(text=labels.CLOSE, callback_data="close_kb"),
    )
    return keyboard.as_markup()


async def person_delete(role: Role, user_tg_id: int):
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        InlineKeyboardButton(text=labels.YES, callback_data=f"confirm_dismiss_{role}_{user_tg_id}")
    )

    keyboard.row(
        InlineKeyboardButton(text=labels.NO, callback_data=f"denied_dismiss_{role}_{user_tg_id}")
    )
    return keyboard.as_markup()


factories_manage = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=labels.ADD_FACTORY, callback_data="add_factory")],
        [InlineKeyboardButton(text=labels.FACTORY_LIST, callback_data="factory_list")],
        [InlineKeyboardButton(text=labels.CLOSE, callback_data="close_kb")],
    ]
)

confirm_factory_add = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=labels.YES, callback_data="add_factory_confirm"),
            InlineKeyboardButton(text=labels.NO, callback_data="add_denied"),
        ],
        [InlineKeyboardButton(text=labels.CLOSE, callback_data="close_kb")],
    ]
)


async def get_factory_page(cur_page: int, key: str = ""):
    keyboard = InlineKeyboardBuilder()

    factories = await requests.get_factories()
    if not factories:
        return None

    pages_num = ceil(len(factories) / KEYBOARD_PAGE_SIZE)
    from_i = KEYBOARD_PAGE_SIZE * (cur_page - 1)
    to_i = min(len(factories), KEYBOARD_PAGE_SIZE * cur_page)
    keyboard = InlineKeyboardBuilder()

    for i in range(from_i, to_i):
        logger.debug(f"{factories[i].id}_{cur_page}")
        keyboard.row(
            InlineKeyboardButton(
                text=factories[i].name,
                callback_data=f"{key}factory_{factories[i].id}_{cur_page}",
            ),
        )

    keyboard.row(
        InlineKeyboardButton(
            text=labels.BACK,
            callback_data=(f"{key}page_factory_{cur_page - 1}" if cur_page - 1 > 0 else "_"),
        ),
        InlineKeyboardButton(text=f"{cur_page}/{pages_num}", callback_data="_"),
        InlineKeyboardButton(
            text=labels.FORWARD,
            callback_data=(f"{key}page_factory_{cur_page + 1}" if cur_page < pages_num else "_"),
        ),
    )
    keyboard.row(
        InlineKeyboardButton(text=labels.CLOSE, callback_data="close_kb"),
    )

    return keyboard.as_markup()


async def manage_factory(fact_id: int, msg_location_id: int):
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        InlineKeyboardButton(
            text=labels.DELETE, callback_data=f"delete_factory_{fact_id}_{msg_location_id}"
        ),
    )

    keyboard.row(
        InlineKeyboardButton(text=labels.RETURN, callback_data=f"factory_list_{msg_location_id}"),
        InlineKeyboardButton(text=labels.CLOSE, callback_data=f"close_kb_{msg_location_id}"),
    )

    return keyboard.as_markup()


async def confirm_delete_fact(fact_id: int, msg_location_id: int):
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        InlineKeyboardButton(
            text=labels.YES, callback_data=f"confirm_delete_factory_{fact_id}_{msg_location_id}"
        ),
        InlineKeyboardButton(
            text=labels.NO, callback_data=f"denied_dismiss_factory_{msg_location_id}"
        ),
    )

    return keyboard.as_markup()
