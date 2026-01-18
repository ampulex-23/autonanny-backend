# Сервисный слой (Services Layer)

## Обзор

Сервисный слой содержит бизнес-логику приложения, вынесенную из роутеров.
Это часть рефакторинга **BE-MVP-003** для улучшения модульности и тестируемости кода.

## Архитектура

```
backend/
├── routers/              # API endpoints (тонкий слой)
│   ├── orders.py        # Обрабатывает HTTP запросы
│   ├── users.py
│   └── ...
│
├── services/            # Бизнес-логика (толстый слой)
│   ├── schedule_service.py   # Логика расписаний
│   ├── route_service.py      # Логика маршрутов
│   ├── order_service.py      # Логика заказов
│   └── ...
│
├── utils/               # Вспомогательные функции
│   └── response_helpers.py
│
└── models/              # ORM модели
    └── ...
```

## Принципы

### 1. **Разделение ответственности (SRP)**
- Роутеры отвечают только за HTTP (валидация запросов, формирование ответов)
- Сервисы содержат всю бизнес-логику
- Модели отвечают за данные

### 2. **Тестируемость**
- Сервисы легко тестировать изолированно
- Не нужно мокать HTTP запросы для тестирования логики

### 3. **Переиспользование**
- Одну и ту же бизнес-логику можно вызывать из разных роутеров
- Или из фоновых задач, CLI команд и т.д.

## Сервисы

### `schedule_service.py`

Управление расписаниями/графиками/контрактами.

**Основные функции:**
- `validate_user_balance()` - проверка баланса пользователя
- `validate_tariff()` - проверка существования тарифа
- `get_tariff_amount()` - получение стоимости тарифа
- `calculate_route_price()` - расчет стоимости маршрута
- `create_schedule_with_roads()` - создание расписания
- `update_schedule_fields()` - обновление расписания
- `delete_schedule()` - удаление расписания

**Пример использования:**
```python
from services.schedule_service import ScheduleService

# Проверка баланса
is_valid, error_response = await ScheduleService.validate_user_balance(user_id)
if not is_valid:
    return error_response

# Создание расписания
schedule = await ScheduleService.create_schedule_with_roads(
    user_id=user_id,
    schedule_data={...},
    roads_data=[...],
    other_params=[...]
)
```

### `route_service.py`

Управление маршрутами расписаний.

**Основные функции:**
- `validate_schedule_access()` - проверка доступа к расписанию
- `create_route()` - создание маршрута
- `update_route()` - обновление маршрута
- `delete_route()` - удаление маршрута
- `save_route_addresses()` - сохранение адресов
- `calculate_route_total_price()` - расчет стоимости
- `get_route_with_details()` - получение маршрута с деталями

**Пример использования:**
```python
from services.route_service import RouteService

# Создание маршрута
route = await RouteService.create_route(
    schedule_id=schedule_id,
    route_data={
        "week_day": 1,
        "title": "Утренний маршрут",
        "start_time": "08:00",
        "end_time": "09:00",
        "type_drive": "0;1"
    },
    children_ids=[1, 2],
    contact_data={
        "name": "Иван",
        "surname": "Иванов",
        "phone": "+79991234567"
    }
)

# Расчет стоимости
total_price, addresses = await RouteService.calculate_route_total_price(
    addresses=addresses_list,
    tariff_amount=100
)
```

### `order_service.py`

Управление заказами и взаимодействием водитель-родитель.

**Основные функции:**
- `get_user_active_orders()` - получение активных заказов
- `get_schedule_responses()` - получение ответов водителей
- `answer_schedule_response()` - ответ на заявку водителя

### `payment_service.py`

Управление платежами через Tinkoff API (BE-MVP-004).

**Основные функции:**
- `generate_tinkoff_token()` - генерация токена для API
- `validate_payment_amount()` - валидация суммы платежа
- `init_sbp_payment()` - инициация платежа через СБП
- `init_card_payment()` - инициация платежа картой
- `check_payment_status()` - проверка статуса платежа
- `add_money_to_balance()` - пополнение баланса
- `get_balance()` - получение баланса
- `get_balance_history()` - история операций

**Пример использования:**
```python
from services.payment_service import PaymentService

# Инициация платежа через СБП
result = await PaymentService.init_sbp_payment(
    user_id=user_id,
    amount=500.0,
    description="Пополнение баланса"
)

# Пополнение баланса после успешной оплаты
await PaymentService.add_money_to_balance(
    user_id=user_id,
    amount=500.0,
    payment_id=payment_id
)
```

### `user_service.py`

Управление профилями пользователей и детьми (BE-MVP-004).

**Основные функции:**
- `get_user_profile()` - получение профиля пользователя
- `update_user_profile()` - обновление профиля
- `get_user_children()` - получение списка детей
- `add_child()` - добавление ребенка
- `update_child()` - обновление данных ребенка
- `delete_child()` - удаление ребенка
- `check_user_role()` - проверка роли пользователя
- `get_extended_user_info()` - расширенная информация

**Пример использования:**
```python
from services.user_service import UserService

# Получение профиля
profile = await UserService.get_user_profile(user_id)

# Добавление ребенка
child_id = await UserService.add_child(
    user_id=user_id,
    child_data={
        "name": "Иван",
        "surname": "Иванов",
        "birthday": "2015-05-10"
    }
)

# Принятие водителя
success = await OrderService.answer_schedule_response(
    user_id=user_id,
    driver_road_id=driver_road_id,
    is_accepted=True
)
```

## Логирование

Все сервисы используют structured logging:

```python
from common.logger import logger

logger.info(
    "Schedule created",
    extra={
        "user_id": user_id,
        "schedule_id": schedule.id,
        "tariff_id": tariff_id
    }
)
```

## Типизация

Все функции имеют type hints:

```python
async def validate_user_balance(user_id: int) -> Tuple[bool, Optional[JSONResponse]]:
    """
    Проверяет баланс пользователя.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Tuple[bool, Optional[JSONResponse]]: (is_valid, error_response)
    """
    ...
```

## Тестирование

Пример теста для сервиса:

```python
import pytest
from services.schedule_service import ScheduleService

@pytest.mark.asyncio
async def test_validate_user_balance_insufficient():
    # Arrange
    user_id = 1
    # Mock DataUserBalance to return balance < 100
    
    # Act
    is_valid, error = await ScheduleService.validate_user_balance(user_id)
    
    # Assert
    assert is_valid is False
    assert error.status_code == 402
```

## Миграция существующего кода

### До (в роутере):
```python
@router.post("/schedule")
async def create_schedule(request: Request, item: NewSchedule):
    # 200+ строк бизнес-логики прямо в роутере
    balance = await DataUserBalance.filter(id_user=request.user).first()
    if not balance or balance.amount < 100:
        return JSONResponse({...}, 402)
    
    tariff = await DataCarTariff.filter(id=item.id_tariff).first()
    # ... еще 180 строк
```

### После (с сервисом):
```python
@router.post("/schedule")
async def create_schedule(request: Request, item: NewSchedule):
    # Валидация баланса
    is_valid, error = await ScheduleService.validate_user_balance(request.user)
    if not is_valid:
        return error
    
    # Валидация тарифа
    if not await ScheduleService.validate_tariff(item.id_tariff):
        return tariff_not_found
    
    # Создание расписания (вся логика в сервисе)
    schedule = await ScheduleService.create_schedule_with_roads(
        user_id=request.user,
        schedule_data={...},
        roads_data=item.roads,
        other_params=item.other_parametrs
    )
    
    return JSONResponse({"status": True, "schedule_id": schedule.id})
```

## Преимущества

1. ✅ **Читаемость**: Роутеры стали короче и понятнее
2. ✅ **Тестируемость**: Легко писать unit-тесты для сервисов
3. ✅ **Переиспользование**: Логику можно вызывать из разных мест
4. ✅ **Масштабируемость**: Легко добавлять новую функциональность
5. ✅ **Поддерживаемость**: Проще находить и исправлять баги

## Следующие шаги

- [ ] Мигрировать оставшиеся эндпоинты из `orders.py`
- [ ] Создать `user_service.py` для `users.py` (BE-MVP-004)
- [ ] Создать `payment_service.py` для платежей (BE-MVP-004)
- [ ] Добавить unit-тесты для всех сервисов
- [ ] Создать интеграционные тесты

## Ссылки

- [Архитектурный принцип 2.2.1](../../docs/TECH_TASK.md)
- [BE-MVP-003](../../docs/BACKEND_TASKS.md#be-mvp-003)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
