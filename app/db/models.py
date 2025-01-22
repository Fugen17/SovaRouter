from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config.db import DB_URL, ObjectLen, UserLen, WorkerTaskLen
from app.config.roles import Role
from app.config.task_status import TaskStatus

engine = create_async_engine(
    url=DB_URL,
    echo=False,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=True)
    fullname: Mapped[str] = mapped_column(String(UserLen.fullname), nullable=True)
    reg_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    role: Mapped[int] = mapped_column(SmallInteger, default=Role.USER, nullable=False)


class Object(Base):

    __tablename__ = "object"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    name: Mapped[str] = mapped_column(String(ObjectLen.name), nullable=False)
    description: Mapped[str] = mapped_column(String(ObjectLen.description), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    __table_args__ = (UniqueConstraint("name", "description", name="uq_name_description"),)


class WorkerTask(Base):

    __tablename__ = "worker_object"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    object_id: Mapped[int] = mapped_column(ForeignKey("object.id"))
    description: Mapped[str] = mapped_column(String(WorkerTaskLen.description), nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    status: Mapped[int] = mapped_column(SmallInteger, default=TaskStatus.WAIT, nullable=False)
    note: Mapped[str] = mapped_column(String(WorkerTaskLen.note), nullable=True)
    completed: Mapped[datetime] = mapped_column(DateTime, nullable=True)


async def db_init():
    """Асинхронная инициализация БД, генерация таблиц."""
    from app.utils import setup_logger

    logger = setup_logger(__name__)

    async with engine.connect() as conn:
        logger.info("Инициализация БД")
        await conn.run_sync(Base.metadata.create_all)
        await conn.commit()
