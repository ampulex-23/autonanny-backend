import re

from tortoise import fields
from tortoise.models import Model
from common.logger import logger


class UsersUser(Model):
    """
    Используется для хранения информации о пользователях.
    Номер телефона не шифруется, но приведен к общему стандарту.
    """
    id = fields.BigIntField(pk=True)
    surname = fields.TextField(null=True)
    name = fields.TextField(null=True)
    phone = fields.TextField()
    isActive = fields.BooleanField(default=True)
    datetime_create = fields.DatetimeField(null=True)


    class Meta:
        schema = "users"
        table = "user"

    def __str__(self):
        return self.id

class UsersChild(Model):
    """
    Таблица для хранения информации о детях пользователей.
    Связь с родителем через id_user (императивный подход).
    BE-MVP-016: Расширенный профиль ребенка
    """
    id = fields.BigIntField(pk=True)
    surname = fields.TextField(null=True)
    name = fields.TextField(null=True)
    patronymic = fields.TextField(null=True)
    child_phone = fields.TextField(null=True)
    age = fields.IntField(null=True)
    birthday = fields.DateField(null=True)  # BE-MVP-016: Дата рождения
    photo_path = fields.TextField(null=True)  # BE-MVP-016: Фото ребенка
    school_class = fields.TextField(null=True)  # BE-MVP-016: Класс/Школа
    character_notes = fields.TextField(null=True)  # BE-MVP-016: Особенности характера
    gender = fields.CharField(max_length=1, null=True)  # BE-MVP-016: Пол (M/F)
    contact_phone = fields.TextField(null=True)  # deprecated - надо удалить
    id_user = fields.BigIntField(null=False)
    isActive = fields.BooleanField(default=True)
    datetime_create = fields.DatetimeField(null=True)

    class Meta:
        schema = "users"
        table = "child"

    def __str__(self):
        return self.id


class UsersReferalUser(Model):
    """
    Используется для хранения информации о рефералах пользователей (партнера и водителя).
    Ссылается на модель UsersUser.
    """
    id = fields.BigIntField(pk=True)
    id_user = fields.BigIntField(null=False)
    id_user_referal = fields.BigIntField(null=False)
    datetime_create = fields.DatetimeField(null=True)


    class Meta:
        schema = "users"
        table = "referal_user"

    def __str__(self):
        return self.id_user


class UsersVerifyAccount(Model):
    """
    Используется для хранении информации о пользователях, которые могут авторизововаться в приложении (Подтвержденные).
    Ссылается на модель UsersUser.
    """
    id = fields.BigIntField(pk=True)
    id_user = fields.BigIntField(null=False)


    class Meta:
        schema = "authentication"
        table = "verify_account"

    def __str__(self):
        return self.id


class UsersUserPhoto(Model):
    """
    Используется для хранении пользовательской аватарки.
    Ссылается на модель UsersUser.
    """
    id = fields.BigIntField(pk=True)
    id_user = fields.BigIntField(null=False)
    photo_path = fields.TextField()


    class Meta:
        schema = "users"
        table = "user_photo"

    def __str__(self):
        return self.id


class WaitDataVerifyRegistration(Model):
    """
    Используется для хранении номеров, которые проходят этап регистрации, но не были подтверждены кодом.
    """
    id = fields.BigIntField(pk=True)
    phone = fields.TextField()


    class Meta:
        schema = "wait_data"
        table = "verify_registration"

    def __str__(self):
        return self.id


class DataTaskBalanceHistory(Model):
    """
    Модель используется для хранения типов платежных операций.
    Можно заменить на константы.
    """
    id = fields.BigIntField(pk=True)
    title = fields.TextField()


    class Meta:
        schema = "data"
        table = "task_balance_history"

    def __str__(self):
        return self.id


class DataUserBalance(Model):
    """
    Используется для храненя текущего баланса пользователей (Клиент, Водитель, Партнёр).
    Ссылается на модель UsersUser.
    """
    id = fields.BigIntField(pk=True)
    id_user = fields.BigIntField(null=False)
    money = fields.DecimalField(10, 2)


    class Meta:
        schema = "data"
        table = "user_balance"

    def __str__(self):
        return self.id


class DataUserBalanceHistory(Model):
    """
    Используется для хранения историй платежей пользоватей.
    Ссылается на модель UsersUser,
    """
    id = fields.BigIntField(pk=True)
    id_user = fields.BigIntField(null=False)
    id_task = fields.BigIntField(null=True)
    description = fields.TextField(null=True)
    money = fields.DecimalField(10, 2)
    datetime_create = fields.DatetimeField(null=True)
    isComplete = fields.BooleanField(null=True)


    class Meta:
        schema = "data"
        table = "user_balance_history"

    def __str__(self):
        return self.id


class DataDebitCard(Model):
    """
    Модель должна использоваться для хранения части информации банковских карт (последних цифр карты, срока годности).
    Ссылается на модель UsersUser.
    """
    id = fields.BigIntField(pk=True)
    id_user = fields.BigIntField(null=False)
    card_number = fields.TextField()
    exp_date = fields.TextField()
    name = fields.TextField()
    isActive = fields.BooleanField(default=True)
    datetime_create = fields.DatetimeField(null=True)


    class Meta:
        schema = "data"
        table = "debit_card"

    def __str__(self):
        return self.id


class HistoryRequestPayment(Model):
    """
    Используется для хранения истории платежей (выплаты).
    Удалить ссылку на карту пользователя.
    Изменить логику и подстроить модель данных.
    Ссылается на модель UsersUser.
    """
    id = fields.BigIntField(pk=True)
    id_user = fields.BigIntField(null=False)
    id_card = fields.BigIntField(null=False)
    id_history = fields.BigIntField(null=False)
    money = fields.DecimalField(10, 2)
    isCashback = fields.BooleanField(default=False)
    isSuccess = fields.BooleanField(default=False)
    isActive = fields.BooleanField(default=True)
    datetime_create = fields.DatetimeField(null=True)


    class Meta:
        schema = "history"
        table = "request_payment"

    def __str__(self):
        return self.id


class UsersFranchiseUser(Model):
    """
    Используется для хранения информации о принадлежании пользователя к франшизе.
    Ссылается на модель UsersUser, UsersFranchise
    """
    id = fields.BigIntField(pk=True)
    id_user = fields.BigIntField(null=False)
    id_franchise = fields.BigIntField(null=False)


    class Meta:
        schema = "users"
        table = "franchise_user"

    def __str__(self):
        return self.id


class HistoryPaymentTink(Model):
    """
    Удалить модель. Не имеем права так делать. Реализовать логику платежей с нуля.
    """
    id = fields.BigIntField(pk=True)
    id_user = fields.BigIntField(null=False)
    id_payment = fields.TextField()
    id_order = fields.TextField()
    amount = fields.BigIntField()
    ip = fields.TextField(null=True)
    token = fields.TextField(null=True)
    card_data = fields.TextField(null=True)
    datetime_create = fields.DatetimeField(null=True)


    class Meta:
        schema = "history"
        table = "payment_tink"

    def __str__(self):
        return self.id


class WaitDataPaymentTink(Model):
    """
    Удалить модель. Не имеем права так делать. Реализовать логику платежей с нуля.
    """
    id = fields.BigIntField(pk=True)
    id_user = fields.BigIntField(null=False)
    id_payment = fields.TextField()
    id_order = fields.TextField()
    amount = fields.BigIntField()
    ip = fields.TextField()
    token = fields.TextField()
    card_data = fields.TextField()
    TdsServerTransID = fields.TextField()
    datetime_create = fields.DatetimeField(null=True)


    class Meta:
        schema = "wait_data"
        table = "payment_tink_data"

    def __str__(self):
        return self.id


class UsersFranchise(Model):
    """
    Используется для хранения информации о франшизах проекта.
    """
    id = fields.BigIntField(pk=True)
    title = fields.TextField(null=True)
    description = fields.TextField(null=True)
    isActive = fields.BooleanField(default=True)
    datetime_create = fields.DatetimeField(null=True)


    class Meta:
        schema = "users"
        table = "franchise"

    def __str__(self):
        return self.id


class UsersFranchiseCity(Model):
    """
    Используется для связи города и франшизы (многие ко многим).
    Ссылается на модель DataCity, UsersFranchise.
    """
    id = fields.BigIntField(pk=True)
    id_franchise = fields.BigIntField(null=False)
    id_city = fields.BigIntField(null=False)


    class Meta:
        schema = "users"
        table = "franchise_city"

    def __str__(self):
        return self.id


class HistoryNotification(Model):
    """
    Используется для хранения информации об ранее отправленных push уведомлений пользователям.
    Не требуется по ТЗ, можно удалить.
    """
    id = fields.BigIntField(pk=True)
    id_user = fields.BigIntField(null=False)
    title = fields.TextField(null=True)
    description = fields.TextField(null=True)
    is_readed = fields.BooleanField(default=False)
    datetime_create = fields.DatetimeField(null=True)


    class Meta:
        schema = "history"
        table = "notification"

    def __str__(self):
        return self.id


class UsersUserVk(Model):
    """
    Используется для хранения информации о связи пользователя и авторизации через ВКонтакте.
    Ссылается на UsersUser.
    Можно оптимизировать, объединив модель с данными UsersUserYandex, ддобавив флаг на тип сервиса.
    """
    id = fields.BigIntField(pk=True)
    id_user = fields.BigIntField(null=False)
    vk_id = fields.TextField(null=True)


    class Meta:
        schema = "users"
        table = "user_vk"

    def __str__(self):
        return self.id


class UsersUserYandex(Model):
    """
    Используется для хранения информации о связи пользователя и авторизации через Яндекс.
    Ссылается на UsersUser.
    Можно оптимизировать, объединив модель с данными UsersUserVk, ддобавив флаг на тип сервиса.
    """

    id = fields.BigIntField(pk=True)
    id_user = fields.BigIntField(null=False)
    yandex_id = fields.TextField(null=True)


    class Meta:
        schema = "users"
        table = "user_yandex"

    def __str__(self):
        return self.id


class UsersPaymentClient(Model):
    """
    Необходима для хранения ключей оплаты для автопополнения баланса по запросу пользователя.
    Ссылается на UsersUser.
    Данные не шифруются.
    """
    id = fields.BigIntField(pk=True)
    id_user = fields.BigIntField(null=False)
    customer_key = fields.TextField(null=False)
    datetime_create = fields.DatetimeField(null=True)


    class Meta:
        schema = "users"
        table = "payment_client"

    def __str__(self):
        return self.id


class ChildEmergencyContact(Model):
    """
    Модель для хранения экстренных контактов детей (BE-MVP-018).
    Используется для связи с родственниками/доверенными лицами в экстренных ситуациях.
    """
    id = fields.BigIntField(pk=True)
    id_child = fields.BigIntField(null=False)  # ID ребенка
    name = fields.TextField(null=False)  # Имя контактного лица
    relationship = fields.TextField(null=False)  # Родство/отношение (мама, папа, бабушка, и т.д.)
    phone = fields.TextField(null=False)  # Телефон в формате +7 (999) 999 99 99
    priority = fields.IntField(default=1)  # Приоритет контакта (1 - первый, 2 - второй и т.д.)
    notes = fields.TextField(null=True)  # Дополнительные заметки
    isActive = fields.BooleanField(default=True)
    datetime_create = fields.DatetimeField(null=True)
    
    class Meta:
        schema = "users"
        table = "child_emergency_contact"
    
    def __str__(self):
        return self.id


class ChildMedicalInfo(Model):
    """
    Модель для хранения медицинской информации детей (BE-MVP-017).
    Содержит информацию об аллергиях, заболеваниях, медикаментах и медицинском полисе.
    """
    id = fields.BigIntField(pk=True)
    id_child = fields.BigIntField(null=False)  # ID ребенка
    
    # Медицинская информация
    allergies = fields.TextField(null=True)  # Аллергии (текстовое описание)
    chronic_diseases = fields.TextField(null=True)  # Хронические заболевания
    medications = fields.TextField(null=True)  # Медикаменты (название, дозировка, график приема)
    medical_policy_number = fields.TextField(null=True)  # Номер медицинского полиса
    blood_type = fields.CharField(max_length=10, null=True)  # Группа крови (A+, B-, O+, AB+ и т.д.)
    
    # Дополнительные заметки
    special_needs = fields.TextField(null=True)  # Особые потребности (инвалидность, диета и т.д.)
    doctor_notes = fields.TextField(null=True)  # Рекомендации врача
    
    # Документы (пути к файлам)
    policy_document_path = fields.TextField(null=True)  # Путь к скану полиса
    medical_certificate_path = fields.TextField(null=True)  # Путь к медицинской справке
    
    # Служебные поля
    isActive = fields.BooleanField(default=True)
    datetime_create = fields.DatetimeField(null=True)
    datetime_update = fields.DatetimeField(null=True)
    
    class Meta:
        schema = "users"
        table = "child_medical_info"
    
    def __str__(self):
        return self.id


class SOSEvent(Model):
    """
    Модель для хранения SOS-событий (BE-MVP-020).
    Используется для экстренных ситуаций с отправкой GPS-координат.
    """
    id = fields.BigIntField(pk=True)
    id_user = fields.BigIntField(null=False)  # Кто активировал SOS (водитель или родитель)
    id_order = fields.BigIntField(null=True)  # Связанный заказ (если есть)
    latitude = fields.FloatField(null=True)  # GPS широта
    longitude = fields.FloatField(null=True)  # GPS долгота
    message = fields.TextField(null=True)  # Дополнительное сообщение
    status = fields.CharField(max_length=20, default='active')  # active, resolved, cancelled
    resolved_by = fields.BigIntField(null=True)  # ID администратора, который разрешил ситуацию
    resolved_at = fields.DatetimeField(null=True)  # Время разрешения
    datetime_create = fields.DatetimeField(null=True)
    
    class Meta:
        schema = "users"
        table = "sos_event"
    
    def __str__(self):
        return self.id


class DriverMeetingCode(Model):
    """
    Модель для хранения кодов встречи водителя с родителем (BE-MVP-021).
    Используется для верификации водителя при передаче ребенка.
    """
    id = fields.BigIntField(pk=True)
    id_driver = fields.BigIntField(null=False)  # ID водителя
    id_schedule_road = fields.BigIntField(null=False)  # ID маршрута
    meeting_code = fields.CharField(max_length=4, null=False)  # 4-значный код
    
    # Статусы
    is_used = fields.BooleanField(default=False)  # Использован ли код
    verified_by = fields.BigIntField(null=True)  # ID родителя, который верифицировал
    verified_at = fields.DatetimeField(null=True)  # Время верификации
    
    # Время действия
    expires_at = fields.DatetimeField(null=False)  # Время истечения кода
    
    # Служебные поля
    isActive = fields.BooleanField(default=True)
    datetime_create = fields.DatetimeField(null=True)
    
    class Meta:
        schema = "users"
        table = "driver_meeting_code"
    
    def __str__(self):
        return self.id


class WeeklyPaymentSchedule(Model):
    """
    Модель для хранения расписания еженедельных списаний (BE-MVP-009).
    Используется для автоматического списания средств за контракты.
    """
    id = fields.BigIntField(pk=True)
    id_user = fields.BigIntField(null=False)  # ID родителя
    id_schedule = fields.BigIntField(null=False)  # ID контракта/графика
    
    # Сумма и карта
    amount = fields.DecimalField(max_digits=10, decimal_places=2, null=False)  # Сумма к списанию
    id_card = fields.BigIntField(null=True)  # ID карты для списания
    
    # Расписание
    next_payment_date = fields.DateField(null=False)  # Дата следующего списания
    last_payment_date = fields.DateField(null=True)  # Дата последнего списания
    
    # Статусы
    status = fields.CharField(max_length=20, default='active')  # active, suspended, cancelled
    failed_attempts = fields.IntField(default=0)  # Количество неудачных попыток
    last_error = fields.TextField(null=True)  # Последняя ошибка
    
    # Служебные поля
    isActive = fields.BooleanField(default=True)
    datetime_create = fields.DatetimeField(null=True)
    datetime_update = fields.DatetimeField(null=True)
    
    class Meta:
        schema = "users"
        table = "weekly_payment_schedule"
    
    def __str__(self):
        return self.id


class WeeklyPaymentHistory(Model):
    """
    Модель для хранения истории еженедельных списаний (BE-MVP-009).
    Логирует все попытки списания средств.
    """
    id = fields.BigIntField(pk=True)
    id_schedule_payment = fields.BigIntField(null=False)  # ID расписания
    id_user = fields.BigIntField(null=False)  # ID родителя
    id_schedule = fields.BigIntField(null=False)  # ID контракта
    
    # Детали платежа
    amount = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    id_card = fields.BigIntField(null=True)  # ID карты
    
    # Результат
    status = fields.CharField(max_length=20, null=False)  # success, failed, pending
    error_message = fields.TextField(null=True)  # Сообщение об ошибке
    payment_id = fields.TextField(null=True)  # ID платежа в платежной системе
    
    # Служебные поля
    datetime_create = fields.DatetimeField(null=True)
    
    class Meta:
        schema = "users"
        table = "weekly_payment_history"
    
    def __str__(self):
        return self.id


