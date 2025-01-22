import os

DB_URL = f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}\
@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"


class UserLen:
    fullname = 40


class ObjectLen:
    name = 30
    description = 50


class WorkerTaskLen:
    note = 100
    description = 100
