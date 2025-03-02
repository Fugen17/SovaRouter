import asyncio
import os
import threading

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message

from app.config.messages import RUNOUT, SUCCEED_LOGIN
from app.utils import setup_logger

logger = setup_logger(__name__)


class ThreadSafeKey:
    _key = None
    _lock = threading.Lock()

    @classmethod
    def add(cls, key: int):
        """Добавляет элемент в множество."""
        with cls._lock:
            logger.debug(f"Set key = {key}")
            cls._key = key

    @classmethod
    def is_valid(cls, key: int):
        """Проверяет, содержится ли элемент в множестве."""
        with cls._lock:
            logger.debug(f"is_valid (our == your): {cls._key} == {key} ?")
            return key == cls._key

    @classmethod
    def clear(cls):
        """Удаляет элемент из множества, если он есть."""
        with cls._lock:
            logger.debug(f"Clear key = {cls._key}")
            cls._key = None


class TimerSingleton:
    _instance = None
    _task = None
    _event = asyncio.Event()
    _lock = asyncio.Lock()
    timeout = int(os.getenv("TIMER", 30))
    message_id = None
    chat_id = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TimerSingleton, cls).__new__(cls)
        return cls._instance

    async def _start_timer(self):
        """Таймер с задержкой в n секунд"""
        logger.debug(f"Таймер начался, ожидаем {self.timeout} секунд...")
        try:
            await asyncio.wait_for(self._event.wait(), timeout=self.timeout)
        except asyncio.TimeoutError:
            await self._delete_message()
        except asyncio.CancelledError:
            logger.debug("Таймер был остановлен вручную.")
            await bot.delete_message(self.chat_id, self.message_id)
        finally:
            ThreadSafeKey.clear()
            self._task = None
            self._event.clear()

    async def _delete_message(self):
        """Удалить сообщение через 30 секунд"""
        if self.message_id is not None and self.chat_id is not None:
            await bot.send_message(self.chat_id, RUNOUT.format(self.timeout))
            await bot.delete_message(self.chat_id, self.message_id)
            logger.debug(f"Сообщение {self.message_id} удалено.")
        else:
            logger.debug("Не удалось найти сообщение для удаления.")

    async def start(self, message: Message, key: int):
        """Запускает таймер и сохраняет ID сообщения"""
        async with self._lock:
            if self._task is not None and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    print("Предыдущий таймер был отменен.")
            ThreadSafeKey.add(key)
            self._event.clear()
            self._task = asyncio.create_task(self._start_timer())
            # Сохраняем ID сообщения и chat_id для дальнейшего удаления
            self.message_id = message.message_id
            self.chat_id = message.chat.id

    async def stop(self, name=None):
        """Останавливает таймер до истечения времени"""
        logger.debug(f"Stop timer ({name})")
        async with self._lock:
            if self._task is not None:
                # Отменяем задачу, если она запущена
                if name:
                    await bot.send_message(self.chat_id, SUCCEED_LOGIN.format(name))
                self._task.cancel()
                self._event.set()


# Global event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

bot = Bot(
    token=os.getenv("TOKEN_BOT"),
    default=DefaultBotProperties(parse_mode="html"),
)
