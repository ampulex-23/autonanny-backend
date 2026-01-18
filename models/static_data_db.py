from tortoise.models import Model
from tortoise import fields
from datetime import datetime


class DataCountry(Model):
    """
    Используется для хранения стран мира (Несмотря на работу проекта только в границах России, права могут быть выданы
     в других странах).
    """
    id = fields.BigIntField(pk=True)
    title = fields.TextField()

    class Meta:
        schema = "data"
        table = "country"

    def __str__(self):
        return self.title


class DataColor(Model):
    """
    Используется для хранения информации об основных цветах окраски автомобилей.
    """
    id = fields.BigIntField(pk=True)
    title = fields.TextField()

    class Meta:
        schema = "data"
        table = "color"

    def __str__(self):
        return self.title


class DataCity(Model):
    """
    Используется для хранения городов России (Проект будет работать только в России).
    """
    id = fields.BigIntField(pk=True)
    title = fields.TextField()

    class Meta:
        schema = "data"
        table = "city"

    def __str__(self):
        return self.title


class DataCarMark(Model):
    """
    Используется для хранения актуальных марок автомобилей.
    """
    id = fields.BigIntField(pk=True)
    title = fields.TextField()

    class Meta:
        schema = "data"
        table = "car_mark"

    def __str__(self):
        return self.title


class DataCarModel(Model):
    """
    Используется для хранения актуальных моделей автомобилей.
    """
    id = fields.BigIntField(pk=True)
    title = fields.TextField()
    id_car_mark = fields.BigIntField(null=False)
    releaseYear = fields.IntField(null=True)

    class Meta:
        schema = "data"
        table = "car_model"

    def __str__(self):
        return self.title


class DataTypeAccount(Model):
    """
    Используется для хранения информации о ролях приложения.
    Можно заменить константами.
    """
    id = fields.BigIntField(pk=True)
    title = fields.TextField()

    class Meta:
        schema = "data"
        table = "type_account"

    def __str__(self):
        return self.title


class DataOtherDriveParametr(Model):
    """
    Используется для хранения информации о дополнительных услугах, доступных пользователям при оформлении поездок
    по графику и разовых.
    """
    id = fields.BigIntField(pk=True)
    title = fields.TextField()
    amount = fields.DecimalField(10, 2)
    isActive = fields.BooleanField(default=True)


    class Meta:
        schema = "data"
        table = "other_drive_parametr"

    def __str__(self):
        return self.title


class DataCarTariff(Model):
    """
    Используется для хранения информации о тарифах.
    Обсуждалось, что у каждой франшизы есть тарифы по умолчанию, но также они могут создавать свои собсвенные,
    стоимость которых будет равна бизнес тарифу.
    Ссылается на модель UsersFranchise.
    """
    id = fields.BigIntField(pk=True)
    title = fields.TextField()  # Тип (Эконом, Бизнес и тд)
    description = fields.TextField(null=True)  # Название
    amount = fields.BigIntField(null=True)
    one_time = fields.BooleanField(default=True)  # Разовый (или по графику)
    percent = fields.BigIntField(null=True)
    photo_path = fields.TextField(null=True)
    id_franchise = fields.BigIntField(null=False)
    isActive = fields.BooleanField(default=True)
    datetime_create = fields.DatetimeField(null=True)


    class Meta:
        schema = "data"
        table = "car_tariff"

    def __str__(self):
        return self.title


class PricingCoefficients(Model):
    """
    BE-MVP-029: Модель для хранения коэффициентов формул расчета стоимости.
    Используется для управления параметрами ценообразования администраторами.
    Соответствует ТЗ раздел 4.4.
    """
    id = fields.BigIntField(pk=True)
    
    # Основные коэффициенты (из ТЗ 4.4.1)
    vm = fields.FloatField(default=27, null=False)  # Средняя скорость движения - км/ч (U_2 в ТЗ)
    s1 = fields.FloatField(default=3, null=False)   # Радиус подачи автомобиля - км
    kc = fields.FloatField(default=3, null=False)   # Коэффициент кэшбека - % (F1 в ТЗ, макс 3%)
    ks = fields.FloatField(default=1, null=False)   # Коэффициент страховки - % (устаревший)
    kg = fields.FloatField(default=1, null=False)   # Городской коэффициент - % (k в ТЗ)
    
    # Новые коэффициенты согласно ТЗ
    t1 = fields.FloatField(default=2.0, null=False)  # Время за 1 км пути - мин (T1 в ТЗ)
    m = fields.FloatField(default=15.0, null=False)  # Стоимость 1 км пути - руб (M в ТЗ)
    x5 = fields.FloatField(default=5.0, null=False)  # Процент на маркетинг - % (X5 в ТЗ, только для разовых)
    p_insurance = fields.FloatField(default=50.0, null=False)  # Страховка - руб (P*** в ТЗ)
    
    # Служебные поля
    is_active = fields.BooleanField(default=True)
    datetime_create = fields.DatetimeField(null=True)
    datetime_update = fields.DatetimeField(null=True)
    updated_by = fields.BigIntField(null=True)  # ID админа, который обновил
    
    class Meta:
        schema = "data"
        table = "pricing_coefficients"
    
    def __str__(self):
        return f"Pricing Coefficients #{self.id}"
