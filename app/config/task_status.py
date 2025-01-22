from enum import IntEnum


class TaskStatus(IntEnum):
    """Класс IntEnum статусов выполения задачи."""

    WAIT = 0
    COMPLETE = 1
    CANCELED = 2

    @property
    def name(self):
        """Переопределение property.

        Returns:
            str: Name in lower case
        """
        return super().name.lower()
