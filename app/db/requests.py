from datetime import date, datetime
from typing import Sequence, Tuple

from sqlalchemy import (
    Date,
    and_,
    case,
    cast,
    desc,
    false,
    func,
    or_,
    select,
    true,
    union,
)
from sqlalchemy.engine.row import Row, RowMapping
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import aliased

from app.config.roles import Role
from app.config.task_status import TaskStatus
from app.db.exceptions import AlreadyExistsError, BadFormatError, BadKeyError, DBError
from app.db.models import Object, User, WorkerTask, async_session
from app.utils import setup_logger

logger = setup_logger(__name__)


async def get_users_by_role(role: Role) -> Sequence[User]:
    """Получение User по Role

    Args:
        role (Role): Роль пользователя. Если нужно выбрать несколько ролей, то используем `|`,
                    например, role = Role.WORKER | Role.MASTER | Role.USER

    Returns:
        Sequence[User]: Массив всех найдённых User.
    """
    logger.debug(f"Получение user'ов ро роли (role={role})")
    async with async_session() as session:
        users = await session.scalars(
            select(User).where(User.role.op("&")(role) != 0).order_by(User.fullname)
        )
        return users.all()


async def get_user(id: int, use_tg: bool = True) -> User:
    logger.debug(f"Получение user (id={id}, use_tg={use_tg})")
    async with async_session() as session:
        condition = User.tg_id if use_tg else User.id
        user: User = await session.scalar(select(User).where(condition == id))

        if not user:
            raise BadKeyError()
        return user


async def set_user(tg_id: int = None) -> User:
    """Добавляет пользователя в таблицу, если тот не сущесвует.

    Args:
        tg_user_id (_type_, optional): Defaults to None.

    Returns:
        int: user_id внутри системы.
    """
    logger.debug(f"Установка user (tg_id={tg_id})")
    async with async_session() as session:
        user: User = await session.scalar(select(User).where(User.tg_id == tg_id))

        if not user:
            logger.info(f"User (tg_id={tg_id}) не существует. Добавляем...")
            user = User(tg_id=tg_id)
            session.add(user)
            await session.commit()
        return user


async def update_user(id: int, values: dict, use_tg: bool = True) -> None:
    """Обновление сущности пользователя.

    Args:
        tg_id (int): tg_user_id
        values (dict): Данные для обновления в формате {User.field1: new_value1,
                                                        User.field2: new_value2}

    Raises:
        DBKeyError: Ошибка неверного ключа.
        DBBadDataError: Ошибка неверного формата данных.
    """
    logger.debug(f"Обновление user (id={id}, use_tg={use_tg}) с values={values.values()}")
    async with async_session() as session:
        condition = User.tg_id if use_tg else User.id
        user: User = await session.scalar(select(User).where(condition == id))

        if not user:
            raise BadKeyError()

        try:
            if User.tg_id in values:
                check_user = await session.scalar(
                    select(User).where(User.tg_id == values.get(User.tg_id))
                )
                if check_user.role == Role.USER:
                    check_user.tg_id = None
                    await session.flush()

            user.tg_id = values.get(User.tg_id, user.tg_id)
            user.fullname = values.get(User.fullname, user.fullname)
            user.role = values.get(User.role, user.role)
            await session.commit()
        except Exception as ex:
            raise BadFormatError(ex)


async def set_factory(name: str, description: str, location: tuple) -> Object:
    """Устанавливет или обновляет завод.

    Args:
        company_name (str): Имя компании завода.
        factory_name (str): Имя завода.

    Returns:
        Object: Сущность завода.
    """
    logger.debug(
        f"Установка factory (name={name}, description={description}, location={location})"
    )
    async with async_session() as session:
        factory = Object(
            name=name,
            description=description,
            latitude=float(location[0]),
            longitude=float(location[1]),
        )
        session.add(factory)
        try:
            await session.commit()
        except IntegrityError:
            raise AlreadyExistsError()
        except Exception as ex:
            raise DBError(ex)
        return factory


async def get_factory(id: int) -> Object:
    logger.debug(f"Получение factory (id={id})")
    async with async_session() as session:
        factory: Object = await session.scalar(select(Object).where(Object.id == id))

        if not factory:
            raise BadKeyError()
        return factory


async def delete_factory(id: int) -> None:
    logger.debug(f"Удаление factory (id={id})")
    async with async_session() as session:
        factory: Object = await session.scalar(select(Object).where(Object.id == id))

        if not factory:
            raise BadKeyError()
        factory.is_deleted = True
        await session.commit()


async def get_factories(deleted: bool = False) -> Sequence[Object]:
    logger.debug(f"Получение factories (deleted={deleted})")
    async with async_session() as session:
        factories = await session.scalars(select(Object).where(Object.is_deleted.is_(deleted)))
        return factories.all()


async def add_task(admin_id: int, user_id: int, object_id: int, description: str) -> WorkerTask:
    logger.debug("add_task to db")
    async with async_session() as session:
        task = WorkerTask(
            admin_id=admin_id, user_id=user_id, object_id=object_id, description=description
        )
        session.add(task)
        try:
            await session.commit()
        except Exception as ex:
            raise DBError(ex)
        return task


async def update_task(task_id: int, status: TaskStatus, note: str = "") -> WorkerTask:
    logger.debug("update_task to db")
    async with async_session() as session:
        task: WorkerTask = await session.scalar(select(WorkerTask).where(WorkerTask.id == task_id))

        if not task:
            raise BadKeyError()
        task.status = status
        task.note = note
        task.completed = datetime.now()
        await session.commit()
        return task


async def get_task(task_id: int) -> WorkerTask:
    logger.debug("get_task to db")
    async with async_session() as session:
        task: WorkerTask = await session.scalar(select(WorkerTask).where(WorkerTask.id == task_id))

        if not task:
            raise BadKeyError()
        return task
