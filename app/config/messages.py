YOUR_ID = "Ваш id: <code>{}</code>"
WORKER_INSTRUCTION = """
Вы являетесь <b>работником</b>.

Вам будут назначаться объекты, которые вы должны проверить.
По всем вопросам обращайтесь к вашему администритору
"""
OWNER_INSTRUCTION = """
Вы являетесь <b>Администратором</b>.

Вам доступно:
- Добавление/удаление объектов
- Добавление/снятие рабочих
- Назначение задач рабочим

Чтобы начать работу:
1. Перешлите бота своим подчинённым (рабочим).
2. Попросите ввести <code>/myid</code>, чтобы получить их <i>tg id</i>
3. Перейдите во вкладку Редактирование -> Рабочие
4. Следуйте инструкциям, чтобы добавить рабочего
"""
ASSIGN_TASK = """
<b>Новая задача</b>

Объект: <i>{}</i>
Описание:
{}
"""
SEND_COMPLETE_TASK = """
Объект <b>{}</b> был <i>{}</i> успешно проверен!

Описание задачи:
{}
"""
EDIT_COMPLETE_TASK = """
Задача <b>{}</b> выполнена!

Описание задачи:
{}
"""

TASK_REASON = "Напишите причину отмены задания:"
EDIT_DENIED_TASK = """
Объект <b>{}</b> был отменён по причине:
<i>{}</i>

Описание задачи:
{}
"""
SEND_DENIED_TASK = """
Задача <b>{}</b> была отменёна <i>{}</i> по причине:
{}

Описание задачи:
{}
"""

EDITING_MENU = "Панель редактирования:"
RETURN_TO_MAIN_MENU = "Возврат в главное меню:"
NO_WORKERS = "Рабочие отсутствуют. Сперва добавьте их во вкладке <b>Редактирование -> Рабочие</b>"
NO_OBJECTS = "Объекты отсутствуют. Сперва добавьте их во вкладке <b>Редактирование -> Объекты</b>"

CHOOSE_WORKER = "Выберите исполнителя:"
CHOOSE_OBJECT = "Выберите объект:"
INPUT_TASK_DESCRIPTION = "Введите описание задания:"
TASK_CREATED = "Задание успешно создано!"

CHOOSE_OPTION = "Выберите действие:"
WORKER_ADD = "Добавление работника:"
ENTER_WORKER_ID = "Отправьте код подключения работнику:\n<code>{}</code>"
ENTER_WORKER_NAME = "Введите ФИО работника"

ADMIN_ADD_CONF = "Добавить админа @{} \nФИО: <b>{}</b>?"
TG_ID_NOT_EXIST = "Аккаунт с таким id не существует"

CANCEL_ADD = "Добавление отменено"
CONFIRM_ADD = "Добавление подтверждено"
RUNOUT = "Прошло {} секунд... Код авторизации сброшен."

GIVE_WORKER_ROLE = "{}, вы были приняты!"
DOESNT_EXIST = (
    "Не удалось добавить пользователя, т.к. он не запускал бота командой /start"
)
WORKER_INFO = "ФИО: {}\nТег: @{}"
DELETE_WORKER = "Хотите удалить рабочего?\nФИО:{}\nТег: @{}"
WORKER_DELETED = "Рабочий удален"
YOU_DISMISSED = "Вы сняты с должности"

OBJECT_DELETED = "Объект удалён"
CONFIRM_DELETE_FACT = "Хотите удалить пару?\nОбъект: {}\nОписание: {}"
OBJECT_INFO = "Объект: {}\nОписание: {}"

ALREADY_EXISTS_OBJECT = "Объект с такими данными уже существует в системе"
OBJECT_ADD_CONFIRM = "Добавить объект?\nазвание: {}\nОписание: {}\nМестоположение: {}"

NOT_LOCATION = "Неправильный формат! Прикрепите своё местоположение"
ENTER_OBJECT_LOCATION = "Прикрепите местоположение объекта:"
ENTER_OBJECT_DESCRIPTION = "Введите описание объекта:"
OBJECT_ADD = "Добавление объекта:"
ENTER_OBJECT_NAME = "Введите название объекта:"
DISMISS_DENIED = "Удаление отменено"
INCORRECT_TG_ID = "Некорректный tg id"
