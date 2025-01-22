from aiogram.fsm.state import State, StatesGroup


class PickAdmin(StatesGroup):
    """States для выбора админа.

    Args:
        StatesGroup (_type_): _description_
    """

    id = State()
    name = State()


class TaskReport(StatesGroup):
    """States для выбора админа.

    Args:
        StatesGroup (_type_): _description_
    """

    id = State()
    msg_id = State()


class PickObject(StatesGroup):
    name = State()
    description = State()
    location = State()


class PickWorker(StatesGroup):
    name = State()
    job = State()
    rate = State()


class AddTask(StatesGroup):
    user_id = State()
    object_id = State()
    description = State()
