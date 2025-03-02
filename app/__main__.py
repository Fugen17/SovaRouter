import threading

from aiogram import Dispatcher
from tomllib import load

from app.db.models import db_init
from app.instances import bot, loop
from app.middlewares.logging import LoggingMiddleware
from app.roles import owner, user, worker
from app.server import run_server
from app.utils import setup_logger

logger = setup_logger(__name__)


async def main():
    """Настройка конфигурации бота и подключение роутеров."""

    await db_init()

    dp = Dispatcher()
    dp.include_routers(user, worker, owner)
    dp.callback_query.middleware(LoggingMiddleware())
    dp.message.middleware(LoggingMiddleware())

    logger.info("Старт бота")
    await dp.start_polling(bot)


def get_version():
    with open("pyproject.toml", "rb") as file:
        data = load(file)
    return data["tool"]["poetry"]["version"]


if __name__ == "__main__":
    # Запуск сервера для переадресации запросов на получение приложение из тг
    logger.info("Запуск сервера в отдельном потоке")
    forwarder_thread = threading.Thread(target=run_server)
    forwarder_thread.daemon = True
    forwarder_thread.start()

    try:
        logger.info(f"Запуск приложения версии {get_version()}")
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Работа приложения прервана")
    except Exception as ex:
        logger.critical(ex)
    finally:
        logger.info("Остановка event loop")
        loop.stop()
