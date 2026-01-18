import datetime
import decimal
import hashlib
import json
import random
import uuid
from pydantic.json_schema import SkipJsonSchema
from bs4 import BeautifulSoup

import requests

from config import settings
from common.logger import logger
from const.drivers_const import *
from const.static_data_const import (DictToModel, access_forbidden,
                                     not_user_photo)
from const.users_const import (AddMoney, ConfirmPayment, DeleteDebitCard,
                               LimitOffset, SbpPayment, StartPayment,
                               UpdateUserData, UserDataPayment, Period,
                               debit_card_not_found, get_money, get_my_card,
                               order_not_found, start_sbp_answer,
                               success_answer, task_to_text, get_user, user_not_found,
                               NewDebitCard, ChildCreate, ChildUpdate, SOSActivate,
                               EmergencyContactCreate, EmergencyContactUpdate,
                               MedicalInfoCreate, MedicalInfoUpdate)
from const.drivers_const import VerifyMeetingCode
from defs import get_websocket_token, get_date_from_datetime, sendPush
from fastapi import APIRouter, HTTPException, Query, Request
from models.authentication_db import (UsersAuthorizationData,
                                      UsersMobileAuthentication,
                                      UsersReferalCode, UsersUserAccount, UsersBearerToken)
from models.drivers_db import UsersCar, UsersDriverData
from models.orders_db import DataScheduleRoadContact, DataScheduleRoadAddress, \
    DataScheduleRoadChild, DataScheduleRoad, DataSchedule, DataScheduleRoadDriver
from models.chats_db import ChatsChat, ChatsChatParticipant
from models.static_data_db import (DataCarMark, DataCarModel, DataColor,
                                   DataTypeAccount)
from models.users_db import (DataDebitCard, DataUserBalance,
                             DataUserBalanceHistory, HistoryPaymentTink,
                             UsersPaymentClient, UsersUser, UsersUserPhoto,
                             UsersVerifyAccount, WaitDataPaymentTink, UsersChild, SOSEvent, HistoryNotification,
                             ChildEmergencyContact, ChildMedicalInfo, DriverMeetingCode,
                             WeeklyPaymentSchedule, WeeklyPaymentHistory)
from utils.response_helpers import generate_responses
from services.payment_service import PaymentService
from services.user_service import UserService


router = APIRouter()

# Backward compatibility alias
generate_tinkoff_token = PaymentService.generate_tinkoff_token


@router.get("/get_me",
            responses=generate_responses([access_forbidden,
                                         get_driver]))
async def get_me(request: Request):
    data = DictToModel(await UsersUser.filter(id=request.user).first().values())
    account = await UsersUserAccount.filter(id_user=request.user).all().values()
    type_account = [x["id_type_account"] for x in account]
    if await UsersVerifyAccount.filter(id_user=request.user).count() == 0 or data.isActive in [False, None]:
        return access_forbidden
    if 2 in type_account and len(type_account) == 1:
        driver_data = DictToModel(await UsersDriverData.filter(id_driver=request.user).first().values())
        referal_code = DictToModel(await UsersReferalCode.filter(id_user=request.user).first().values())
        photo = await UsersUserPhoto.filter(id_user=request.user).first().values("photo_path")
        photo = photo["photo_path"] if photo is not None and "photo_path" in photo else not_user_photo
        car_data = DictToModel(await UsersCar.filter(id=driver_data.id_car).first().values())
        car = {"mark": (await DataCarMark.filter(id=car_data.id_car_mark).first().values())["title"],
               "model": (await DataCarModel.filter(id=car_data.id_car_model).first().values())["title"],
               "color": (await DataColor.filter(id=car_data.id_color).first().values())["title"],
               "year": car_data.year_create,
               "state_number": car_data.state_number,
               "ctc": car_data.ctc
               }
        return JSONResponse({"status": True,
                             "message": "Success!",
                             "me": {
                                 "token": await get_websocket_token(request.user),
                                 "referal_code": referal_code.code,
                                 "surname": data.surname,
                                 "name": data.name,
                                 "phone": data.phone,
                                 "role": ["Водитель"],
                                 "inn": None if hasattr(driver_data, "inn") is True else driver_data.inn,
                                 "photo_path": photo,
                                 "video_path": driver_data.video_url,
                                 "date_reg": data.datetime_create.isoformat(),
                                 "carData": car,
                                 "hasAuth": False if await UsersMobileAuthentication.filter(
                                                id_user=request.user).count() == 0 else True
                            }})
    else:
        photo = await UsersUserPhoto.filter(id_user=request.user).first().values("photo_path")
        photo = photo["photo_path"] if photo is not None and "photo_path" in photo else not_user_photo
        role = await DataTypeAccount.filter(id__in=type_account).all().values()
        return JSONResponse({"status": True,
                             "message": "Success!",
                             "me": {
                                 "token": await get_websocket_token(request.user),
                                 "surname": data.surname,
                                 "name": data.name,
                                 "phone": data.phone,
                                 "role": [x["title"] for x in role],
                                 "photo_path": photo,
                                 "date_reg": data.datetime_create.isoformat(),
                                 "hasAuth": False if await UsersMobileAuthentication.filter(
                                     id_user=request.user).count() == 0 else True
                             }})


@router.put(
    "/update_me", responses=generate_responses([success_answer, access_forbidden])
)
async def update_me_data(request: Request, item: UpdateUserData):
    """
    Обновляет данные пользователя. Ни одно поле не является обязательным.

    Args:
        request (Request): Запрос.
        item (UpdateUserData): Данные пользователя.

    Validation:
        surname, name - должны быть строкой,
        телефон СТРОГО формата "+7 (999) 999 99 99",
        пароль длиной более 8 символов.

    Returns:
        JSONResponse: Сообщение об успешном обновлении данных, либо сообщение об ошибке.
    """

    user = DictToModel(await UsersUser.filter(id=request.user).first().values())
    user_photo = await UsersUserPhoto.filter(id_user=request.user).first().values()
    if item is not None:
        # BE-MVP-026: Фильтрация нецензурных слов в профиле
        from utils.profanity_filter import filter_profanity
        
        if (
            item.surname != user.surname
            and item.surname is not None
            and len(item.surname) > 0
        ):
            filtered_surname, was_filtered = filter_profanity(item.surname)
            if was_filtered:
                logger.warning(
                    f"Profanity filtered in surname for user {request.user}",
                    extra={"user_id": request.user, "event_type": "profile_surname_profanity_filtered"}
                )
            await UsersUser.filter(id=request.user).update(surname=filtered_surname)
            
        if item.name != user.name and item.name is not None and len(item.name) > 0:
            filtered_name, was_filtered = filter_profanity(item.name)
            if was_filtered:
                logger.warning(
                    f"Profanity filtered in name for user {request.user}",
                    extra={"user_id": request.user, "event_type": "profile_name_profanity_filtered"}
                )
            await UsersUser.filter(id=request.user).update(name=filtered_name)
        if item.password is not None and len(item.password) > 0:
            await UsersAuthorizationData.filter(id_user=request.user).update(
                password=str((hashlib.md5(item.password.encode())).hexdigest())  # noqa
            )

        if item.phone != user.phone and item.phone is not None and len(item.phone) > 0:
            cleaned_phone = '+' + ''.join(filter(str.isdigit, item.phone[1:]))
            await UsersUser.filter(id=request.user).update(phone=cleaned_phone)

        if item.photo_path and len(item.photo_path) > 0:  # Может надо, может нет.
            if user_photo and user_photo.get("photo_path") != item.photo_path:
                await UsersUserPhoto.filter(id_user=request.user).update(
                    photo_path=item.photo_path
                )
            elif not user_photo:
                await UsersUserPhoto.create(
                    id_user=request.user, photo_path=item.photo_path
                )

        return success_answer
    return access_forbidden


@router.get("/get_user", responses=generate_responses([get_user, access_forbidden,
                                                       user_not_found]))
async def get_user(request: Request, user_id: int):
    """
    Возвращает данные пользователя.

    Args:
        request (Request): Запрос.
        user_id (int): ID пользователя.

    Returns:
        JSONResponse: Данные пользователя.
    """

    if (
        await UsersUserAccount.filter(
            id_user=request.user, id_type_account__in=[6, 7]
        ).count()
        == 0
    ):
        return access_forbidden
    user: dict = await UsersUser.filter(id=user_id).first().values()
    if not user:
        return user_not_found
    user_photo: dict = await UsersUserPhoto.filter(id_user=user_id).first().values()
    user_photo: str = (
        not_user_photo
        if user_photo is None or "photo_path" not in user_photo
        else user_photo["photo_path"]
    )
    user["photo_path"] = user_photo
    user["datetime_create"] = await get_date_from_datetime(user["datetime_create"])
    user_id_type_account_dict: dict = (
        await UsersUserAccount.filter(id_user=user_id).first().values("id_type_account")
    )
    user_id_type_account: int = int(user_id_type_account_dict["id_type_account"])
    user_type_account_dict: dict = (
        await DataTypeAccount.filter(id=user_id_type_account).first().values("title")
    )
    user_type_account: str = user_type_account_dict["title"]
    user["type_account"] = user_type_account

    if user_id_type_account == 2:
        user_driver_dict: dict = (
            await UsersDriverData.filter(id_driver=user_id)
            .first()
            .values("video_url", "id_car", "inn")
        )

        if not user_driver_dict:
            return JSONResponse({"status": True, "message": "Success!", "user": user})

        user_driver_video_url: str = (
            user_driver_dict["video_url"] if user_driver_dict["video_url"] else "None"
        )
        user["driver_video"] = user_driver_video_url
        user_driver_inn: str = user_driver_dict["inn"]
        user["driver_inn"] = user_driver_inn
        user_car_id: str = user_driver_dict["id_car"]
        user_car: dict = {}

        if user_car_id:
            car: dict = await UsersCar.filter(id=user_car_id).first().values()
            car_mark: dict = (
                await DataCarMark.filter(id=car["id_car_mark"]).first().values()
            )
            car_model: dict = (
                await DataCarModel.filter(id=car["id_car_model"]).first().values()
            )
            car_color: dict = (
                await DataColor.filter(id=car["id_color"]).first().values()
            )
            user_car["mark"] = car_mark["title"]
            user_car["model"] = car_model["title"]
            user_car["color"] = car_color["title"]
            user_car["year"] = car["year_create"]
            user_car["state_number"] = car["state_number"]
            user_car["ctc"] = car["ctc"]
            user["car"] = user_car

    return JSONResponse({"status": True, "message": "Success!", "user": user})


@router.post("/money", responses=generate_responses([get_money]))
async def get_my_money(
    request: Request,
    item: Union[LimitOffset, None] = None,
    period: Union[Period, SkipJsonSchema[None]] = None,
):
    """
    Обрабатывает запрос на получение баланса пользователя и истории операций.

    Args:
        request (Request): Объект запроса.
        item (LimitOffset): Для пагинации. ПОКА НЕ РЕАЛИЗОВАНО.
        period (str): Период. Query-параметр.
            Может быть только: `current_day`, `current_week`, `current_month`, `current_year`.

    Example:

        Пример успешного ответа:

        {
          "status": true,
          "message": "Success!",
          "balance": 23,
          "income": [
            10,
            37,
          ],
          "expenses": [
            -12,
            -12,
          ],
          "history": [
            {
              "description": "Зачисление бонусов от Франшизы",
              "title": "Начисление бонусов",
              "date": "10/5",
              "amount": "10.00"
            },
            {
              "description": "Зачисление бонусов от Франшизы",
              "title": "Начисление бонусов",
              "date": "10/5",
              "amount": "37.00"
            },
            {
              "description": "Начисление комиссии от Франшизы",
              "title": "Начисление комиссии",
              "date": "7/11",
              "amount": "-12.00"
            },
            {
              "description": "Начисление комиссии от Франшизы",
              "title": "Начисление комиссии",
              "date": "7/11",
              "amount": "-12.00"
            },
          ]
        }


    Returns:
        JSONResponse: Баланс пользователя и история операций.
    """

    now = datetime.datetime.now()
    if period == Period.current_day.value:
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == Period.current_week.value:
        start_date = now - datetime.timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == Period.current_month.value:
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == Period.current_year.value:
        start_date = now.replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        return JSONResponse(
            {"status": False, "message": "Invalid period."}, status_code=400
        )

    balance = await DataUserBalance.filter(id_user=request.user).first().values()
    if balance is None or len(balance) == 0:
        await DataUserBalance.create(id_user=request.user, money=decimal.Decimal(0.0))
        balance = {"money": 0.0}

    history = (
        await DataUserBalanceHistory.filter(
            id_user=request.user,
            isComplete=True,
            datetime_create__gte=start_date,
            datetime_create__lte=end_date,
        )
        .exclude(id_task=-100)
        .values()
    )

    income_list = []
    expenses_list = []
    detailed_history = []

    for each in history:
        if each["money"] > 0:
            income_list.append(float(each["money"]))
        else:
            expenses_list.append(float(each["money"]))

        each["title"] = task_to_text.get(each["id_task"], "Unknown Task")
        each["date"] = (
            f"{each['datetime_create'].date().day}/{each['datetime_create'].date().month}"
        )
        each["amount"] = str(each["money"])
        del each["id"]
        del each["money"]
        del each["id_task"]
        del each["id_user"]
        del each["isComplete"]
        del each["datetime_create"]

        detailed_history.append(each)

    return JSONResponse(
        {
            "status": True,
            "message": "Success!",
            "balance": float(balance["money"]),
            "income": income_list,
            "expenses": expenses_list,
            "history": detailed_history,
        }
    )


@router.post("/get-my-card",
             responses=generate_responses([get_my_card]))
async def get_my_debit_card(request: Request):
    data = await DataDebitCard.filter(id_user=request.user, isActive__in=[True, False]).order_by("-id").all().values()
    for card in data:
        if int(card["card_number"][0]) in [5, 6]:
            card["bank"] = "MasterCard"
        elif int(card["card_number"][0]) == 4:
            card["bank"] = "Visa"
        elif int(card["card_number"][0]) == 2:
            card["bank"] = "Mir"
        else:
            card["bank"] = "Your Bank"
        card_date = card["exp_date"].split("/")
        if card["isActive"] is True and ((int("20"+card_date[1]) < datetime.datetime.now().year) or
            (int("20"+card_date[1])==datetime.datetime.now().year and int(card_date[0])<datetime.datetime.now().month)):
            await DataDebitCard.filter(id=card["id"]).update(isActive=False)
            card["isActive"] = False
        card["name"] = card["name"].upper()
        card["full_number"] = card["card_number"]
        card["card_number"] = f"****{card['card_number'][-4]}{card['card_number'][-3]}" \
                              f"{card['card_number'][-2]}{card['card_number'][-1]}"
        del card["id_user"]
        del card["datetime_create"]
    return JSONResponse({"status": True,
                         "message": "Success!",
                         "cards": data,
                         "total": len(data)})


@router.post("/add-my-card")
async def add_debit_card(request: Request, item: NewDebitCard):
    await DataDebitCard.create(id_user=request.user,
                               card_number=item.card_number,
                               exp_date=item.exp_date,
                               name=item.name)
    return JSONResponse({"status": True,
                         "message": "Success!"})


@router.post("/delete-my-card",
             responses=generate_responses([success_answer,
                                           debit_card_not_found]))
async def delete_debit_card(request: Request, item: DeleteDebitCard):
    if await DataDebitCard.filter(id=item.id, id_user=request.user).count() == 0:
        return debit_card_not_found
    await DataDebitCard.filter(id=item.id).update(isActive=None)
    return success_answer


@router.post("/start_sbp_payment", responses=generate_responses([start_sbp_answer]))
async def start_sbp_payment(request: Request, item: SbpPayment):
    """
    Инициирует процесс оплаты через СБП с использованием Tinkoff API.
    Затем через некоторое время - следует обратиться к `/add_money` для проверки
    статуса платежа и начислении средств на баланс клиента.

    Args:
        request (Request): HTTP-запрос с данными пользователя.
        item (SbpPayment): Данные для создания платежа, включая сумму, телефон и email.

    Returns:
        JSONResponse: Ответ с информацией об успешности операции и ссылкой на оплату.

    Пример запроса:
    {
        "amount": 1000,  // Сумма платежа в копейках
        "email": "user@example.com",
        "phone": "+79991234567"  // Разрешены только цифры, исключение — первый символ может быть +.
    }

    Пример ответа:
    {
        "status": True,
        "message": "Success!",
        "payment": {
            "amount": 1000,
            "PaymentId": "123456789",
            "payment_url": "https://qr.nspk.ru/AS1000670LSS7DN18SJQDNP4B05KLJL2?type=01&bank=100000000001&sum=10000&cur=RUB&crc=C08B"
        }
    }

    Raises:
        HTTPException: Выбрасывается при ошибке инициализации платежа с кодом 505 и деталями ошибки.
    """
    try:
        # Инициация платежа через сервис (сумма в копейках, конвертируем в рубли)
        amount_rubles = item.amount / 100
        result = await PaymentService.init_sbp_payment(
            user_id=request.user,
            amount=amount_rubles,
            description="Пополнение баланса аккаунта АвтоНяня"
        )
        
        # Сохраняем историю платежа
        await HistoryPaymentTink.create(
            id_user=request.user,
            id_payment=result["PaymentId"],
            id_order=result["OrderId"],
            amount=item.amount,
        )
        
        return JSONResponse({
            "status": True,
            "message": "Success!",
            "payment": {
                "amount": item.amount,
                "PaymentId": result["PaymentId"],
                "payment_url": result.get("PaymentURL") or result.get("Data"),
            },
        })
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        logger.error(f"SBP payment failed: {e}", extra={"user_id": request.user})
        raise HTTPException(505, detail=str(e))


@router.post("/start_payment")
async def generate_url_for_payment(request: Request, item: UserDataPayment):
    """
    Генерирует ссылку для проведения платежа через Tinkoff, проверяет версию 3DS.
    Если версия 3DS - не 2.x.x, то сразу инициализирует оплату.
    Если версия 3DS - 2.x.x, то в дальнейшем потребуется завершить оплату через `/confirm_payment`.

    Пример запроса:
        {
          "ip": "02a3:06f0:0004:0000:0000:0000:0000:0edf",  // (опционально)
          "amount": 50000,
          "card_data": "U5jDbwqOVx+2vDApx...zRZ87GdWeY8wgg==",  // в зашифрованном виде
          "email": "user@example.com",
          "phone": "+79991234567",
          "recurrent": "true"  // (опционально)
        }

    Пример ответа при версии 3DS 2.x.x (скорее всего такая версия и будет):
        {
          "is3DsVersion2": True,
          "TerminalKey": "1692261610441",
          "PaymentId": 10063,
          "serverTransId": "17d3791b-5cfa-4318-bc23-3d949e8c4b7e",  # Уникальный идентификатор транзакции, который генерируется 3DS-Server.
          "ThreeDSMethodURL": "https://acs.vendorcert.mirconnect.ru/ds/6300",  # Дополнительный параметр для 3DS второй версии, который позволяет пройти этап по сбору данных браузера ACS-ом.
        }

    Args:
        request (Request): Объект запроса, содержащий информацию о пользователе.
        item (UserDataPayment): Данные для оплаты, включая сумму, email, телефон, IP-адрес и зашифрованные данные карты.

    Returns:
        JSONResponse: JSON-ответ с информацией о статусе операции, параметрами для 3DS-аутентификации и ссылкой на ACS.

    Raises:
        HTTPException: В случае ошибки на любом этапе процесса оплаты.
    """


    # Валидация минимальной суммы
    if item.amount < 10000:  # 100 руб = 10000 копеек
        raise HTTPException(400, detail="Минимальная сумма пополнения: 100 руб")
    
    logger.info(f"Starting payment for user {request.user}, amount: {item.amount}")
    content_type = {"Content-Type": "application/json"}
    order_id = hashlib.md5(
        str(("%032x" % random.getrandbits(128)) + str(request.user)).encode()
    ).hexdigest()
    data = {
        "TerminalKey": settings.tinkoff_terminal_key,
        "Amount": item.amount,  # Сумма в копейках. Например, 3 руб. 12коп. — это число 312.
        "OrderId": order_id,  # Идентификатор заказа в системе мерчанта. Должен быть уникальным для каждой операции.
        "Description": "Пополнение баланса аккаунта АвтоНяня",  # Описание заказа. Значение параметра будет отображено на платежной форме.
        "SuccessURL": f"https://nynyago.ru/api/v1.0/payments/payments_success?order_id={order_id}",  # URL на веб-сайте мерчанта, куда будет переведен клиент в случае успешной оплаты — настраивается в личном кабинете. Если параметр:
        "NotificationURL": f"https://nynyago.ru/api/v1.0/payments/payments_status/{order_id}",  # URL на веб-сайте мерчанта, куда будет отправлен POST-запрос о статусе выполнения вызываемых методов — настраивается в личном кабинете
        "FailURL": "https://nynyago.ru/api/v1.0/payments/payments_unsuccessful?order_id={order_id}",  # URL на веб-сайте мерчанта, куда будет переведен клиент в случае неуспешной оплаты — настраивается в личном кабинете. Если параметр:
        "PayType": "O",  # Определяет тип проведения платежа: O — одностадийная оплата
        "DATA": {
            "Phone": item.phone,
            "Email": item.email,
            "TinkoffPayWeb": "true",
            "Device": "Mobile",
            "DeviceOs": "Android",
            "DeviceWebView": "true",
            "DeviceBrowser": "Chrome",
        },
    }
    init_data = requests.post(
        f"{settings.tinkoff_api_url}/Init", json=data, headers=content_type
    ).json()
    logger.info(f"Tinkoff Init response: {init_data}", extra={"user_id": request.user, "order_id": order_id})
    if init_data["Success"] is False:
        logger.error(f"Tinkoff Init failed: {init_data}", extra={"user_id": request.user})
        raise HTTPException(505, detail=init_data)
    check_data = {
        "PaymentId": init_data["PaymentId"],
        "TerminalKey": settings.tinkoff_terminal_key,
        "CardData": item.card_data,  # Зашифрованные данные карты. Например: "U5jDbwqOVx+2vDApx...zRZ87GdWeY8wgg=="
        "Token": generate_tinkoff_token(item.amount, init_data["PaymentId"]),
    }
    check_3ds_data = requests.post(
        f"{settings.tinkoff_api_url}/Check3dsVersion",  # Проверяет поддерживаемую версию 3DS-протокола по карточным данным из входящих параметров.
        json=check_data,
        headers=content_type,
    ).json()
    logger.info(check_3ds_data)
    if item.ip is None:
        item.ip = "02a3:06f0:0004:0000:0000:0000:0000:0edf"
    if check_3ds_data["Success"] is False:
        print(check_3ds_data)
        raise HTTPException(506, detail=check_3ds_data)
    if check_3ds_data["Version"] == "2.1.0":
        await WaitDataPaymentTink.create(
            id_user=request.user,
            id_payment=init_data["PaymentId"],
            id_order=order_id,
            card_data=item.card_data,
            ip=item.ip,
            amount=item.amount,
            token=generate_tinkoff_token(item.amount, init_data["PaymentId"]),
            TdsServerTransID=check_3ds_data["TdsServerTransID"],  # Уникальный идентификатор транзакции, который генерируется 3DS-Server.
        )
        return JSONResponse(
            {
                "is3DsVersion2": True,
                "TerminalKey": settings.tinkoff_terminal_key,
                "PaymentId": init_data["PaymentId"],
                "serverTransId": check_3ds_data["TdsServerTransID"],  # Уникальный идентификатор транзакции, который генерируется 3DS-Server.
                "ThreeDSMethodURL": check_3ds_data["ThreeDSMethodURL"],  # Дополнительный параметр для 3DS второй версии, который позволяет пройти этап по сбору данных браузера ACS-ом.
            }
        )
    confirm_payment = {
        "PaymentId": init_data["PaymentId"],
        "TerminalKey": settings.tinkoff_terminal_key,
        "Token": generate_tinkoff_token(item.amount, init_data["PaymentId"]),
        "IP": item.ip,  # IP-адрес клиента. Обязательный параметр для 3DS второй версии. DS платежной системы требует передавать данный адрес в полном формате, без каких-либо сокращений — 8 групп по 4 символа.
        "CardData": item.card_data,
        "Amount": item.amount,
        "deviceChannel": "02",  # Канал устройства. 02 - Browser.
    }
    if item.email is not None and len(item.email) > 0:
        confirm_payment["SendEmail"] = True
        confirm_payment["InfoEmail"] = item.email
    confirm_payment_data = requests.post(
        f"{settings.tinkoff_api_url}/FinishAuthorize",  # Метод подтверждает платеж передачей реквизитов. При одностадийной оплате — списывает средства с карты клиента.
        json=confirm_payment,
        headers=content_type,
    ).json()
    logger.info(confirm_payment_data)
    token = generate_tinkoff_token(item.amount, init_data["PaymentId"])
    await HistoryPaymentTink.create(
        id_order=order_id,
        amount=item.amount,
        id_user=request.user,
        ip=item.ip,
        card_data=item.card_data,
        token=token,
        id_payment=init_data["PaymentId"],
    )
    if confirm_payment_data["Success"] is False:
        print(confirm_payment_data)
        raise HTTPException(507, detail=confirm_payment_data)
    if confirm_payment_data["Status"] == "3DS_CHECKING":
        logger.info("3DS_CHECKING")
        acs_url = confirm_payment_data["ACSUrl"]
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        form_data = {
            "TermUrl": "https://nyanyago.ru/3ds-callback",
            "MD": confirm_payment_data["MD"],
            "PaReq": confirm_payment_data["PaReq"]
        }
        acs_request = requests.post(acs_url, data=form_data, headers=headers)
        logger.info(f"ACS Request Status Code: {acs_request.status_code}")
        return JSONResponse(
            {
                "status": True,
                "message": "Success!",
                "PaymentId": init_data["PaymentId"],
                "HTML": acs_request.text,
                "is3DsVersion2": (
                    True
                    if check_3ds_data["Version"] == "2.1.0"
                    else False if check_3ds_data["Version"] == "1.0.0" else None
                ),
                "serverTransId": (
                    check_3ds_data["TdsServerTransID"]
                    if "TdsServerTransID" in check_3ds_data
                       and check_3ds_data["TdsServerTransID"] is not None
                    else None
                ),
                "acsUrl": confirm_payment_data["ACSUrl"],
                "md": confirm_payment_data["MD"],
                "paReq": confirm_payment_data["PaReq"],
                "TerminalKey": settings.tinkoff_terminal_key,
                "acsTransId": (
                    None
                    if "AcsTransId" not in confirm_payment_data
                       or confirm_payment_data["AcsTransId"] is None
                    else confirm_payment_data["AcsTransId"]
                ),
            }
        )

    return JSONResponse(
        {
            "status": True,
            "message": "Success!",
            "PaymentId": init_data["PaymentId"],
            "is3DsVersion2": (
                True
                if check_3ds_data["Version"] == "2.1.0"
                else False if check_3ds_data["Version"] == "1.0.0" else None
            ),
            "serverTransId": (  # Уникальный идентификатор транзакции, который генерируется 3DS-Server.
                check_3ds_data["TdsServerTransID"]
                if "TdsServerTransID" in check_3ds_data
                and check_3ds_data["TdsServerTransID"] is not None
                else None
            ),
            "acsUrl": confirm_payment_data["ACSUrl"],  # Если в ответе метода FinishAuthorize возвращается статус 3DS_CHECKING, мерчанту нужно сформировать запрос на URL ACS банка, который выпустил карту — параметр ACSUrl в ответе, и вместе с этим перенаправить клиента на эту же страницу ACSUrl для прохождения 3DS.
            "md": confirm_payment_data["MD"],  # Уникальный идентификатор транзакции в системе Т‑Кассы.
            "paReq": confirm_payment_data["PaReq"],  # Шифрованная строка, содержащая результаты 3-D Secure аутентификации. Возвращается в ответе от ACS.
            "TerminalKey": settings.tinkoff_terminal_key,
            "acsTransId": (  # Идентификатор транзакции, присвоенный ACS, который вернулся в ответе FinishAuthorize. Может и не быть...
                None
                if "AcsTransId" not in confirm_payment_data
                or confirm_payment_data["AcsTransId"] is None
                else confirm_payment_data["AcsTransId"]
            ),
        }
    )


@router.post("/confirm_payment")
async def confirm_payment_3dsV2(request: Request, item: ConfirmPayment):
    """
    Завершает платёж (последовательный шаг после обращения к `/start_payment`).
    Только при версии 3DS 2.x.x.
    Затем через некоторое время - следует обратиться к `/add_money` для проверки
    статуса платежа и начислении средств на баланс клиента.

    Пример запроса:
        {
            "PaymentId": 1, // Уникальный идентификатор транзакции, который возвращается из `/start_payment`.
            "DATA": {}, // JSON-объект, который содержит дополнительные параметры в виде ключ:значение. Эти параметры будут переданы на страницу оплаты
            "email": "example@gmail.com"
        }
    Args:
        request (Request): Запрос.
        item (ConfirmPayment): Данные пользователя: PaymentId, DATA, email.

    Returns:
        JSONResponse: Ответ.
    """

    content_type = {"Content-Type": "application/json"}
    data = (
        await WaitDataPaymentTink.filter(
            id_user=request.user, id_payment=item.PaymentId
        )
        .first()
        .values()
    )
    if data is None:
        return order_not_found
    await WaitDataPaymentTink.filter(
        id_user=request.user, id_payment=item.PaymentId
    ).delete()
    confirm_payment = {
        "PaymentId": item.PaymentId,
        "TerminalKey": settings.tinkoff_terminal_key,
        "Token": generate_tinkoff_token(data['amount'], item.PaymentId),
        "IP": data["ip"],
        "CardData": data["card_data"],
        "Amount": data["amount"],
        "deviceChannel": "02",
        "DATA": item.DATA,
    }
    if item.email is not None and len(item.email) > 0:
        confirm_payment["SendEmail"] = True
        confirm_payment["InfoEmail"] = item.email
    confirm_payment_data = requests.post(
        f"{settings.tinkoff_api_url}/FinishAuthorize",
        json=confirm_payment,
        headers=content_type,
    ).json()
    token = generate_tinkoff_token(data['amount'], item.PaymentId)
    await HistoryPaymentTink.create(
        id_order=data["id_order"],
        amount=data["amount"],
        id_user=request.user,
        ip=data["ip"],
        card_data=data["card_data"],
        token=token,
        id_payment=item.PaymentId,
    )
    print(confirm_payment_data)
    if confirm_payment_data["Success"] is False:
        print(confirm_payment_data)
        raise HTTPException(507, detail=confirm_payment_data)
    return JSONResponse(
        {
            "status": True,
            "message": "Success!",
            "is3DsVersion2": True,
            "serverTransId": confirm_payment_data["TdsServerTransId"],
            "acsUrl": (
                confirm_payment_data["ACSUrl"]
                if "ACSUrl" in confirm_payment_data
                else None
            ),
            "md": confirm_payment_data["MD"] if "MD" in confirm_payment_data else None,
            "paReq": (
                confirm_payment_data["PaReq"]
                if "PaReq" in confirm_payment_data
                else None
            ),
            "TerminalKey": settings.tinkoff_terminal_key,
            "acsTransId": (
                None
                if "AcsTransId" not in confirm_payment_data
                or confirm_payment_data["AcsTransId"] is None
                else confirm_payment_data["AcsTransId"]
            ),
        }
    )


@router.post("/add_money", responses=generate_responses([success_answer]))
async def add_money(request: Request, item: AddMoney):
    """
    Добавляет средства на баланс пользователя.

    Пример запроса:
        {
            "amount": 100,  // тут уже в рублях
            "payment_id": 1
        }

    Args:
        request (Request): Запрос.
        item (AddMoney): Данные пользователя: amount, payment_id.

    Returns:
        JSONResponse: Ответ.
    """
    content_type = {"Content-Type": "application/json"}
    if (
        await HistoryPaymentTink.filter(
            id_user=request.user, id_payment=item.payment_id
        )
        == 0
    ):
        raise HTTPException(404, "Payment id not found or not your!")

    pay = (
        await HistoryPaymentTink.filter(id_payment=item.payment_id, id_user=request.user)
        .first()
        .values()
    )
    data = {
        "TerminalKey": settings.tinkoff_terminal_key,
        "PaymentId": item.payment_id,
        "Token": pay["token"],
    }
    x = requests.post(
        f"{settings.tinkoff_api_url}/GetState", json=data, headers=content_type  # Метод возвращает статус платежа.
    ).json()
    print(x)
    if x["Status"] not in ["CONFIRMING", "CONFIRMED"]:
        raise HTTPException(402, "Unsuccessful update balance!")
    user = await DataUserBalance.filter(id_user=request.user).first().values()
    if user is None:
        await DataUserBalance.create(id_user=request.user, money=item.amount)
    user = await DataUserBalance.filter(id_user=request.user).first().values()
    await DataUserBalance.filter(id_user=request.user).update(
        money=user["money"] + decimal.Decimal(item.amount)
    )
    await DataUserBalanceHistory.create(
        id_user=request.user,
        money=decimal.Decimal(item.amount),
        id_task=-1,
        isComplete=True,
        description="Пополнение баланса пользователя с банковской карты",
    )
    return success_answer


@router.post("/start-payment", responses=generate_responses([success_answer]))
async def start_tinkoff_payment(request: Request, item: StartPayment):
    """
    Походу deprecated
    """
    print(item.__dict__)
    terminal_key = "1692261610441"
    password = "cz9mvi6nawsft86w"
    content_type = {"Content-Type": "application/json"}
    order_id = hashlib.md5(
        str(("%032x" % random.getrandbits(128)) + str(request.user)).encode()
    ).hexdigest()
    token = hashlib.sha256(
        f"{item.amount}{order_id}{password}{terminal_key}".encode()
    ).hexdigest()
    if await UsersPaymentClient.filter(id_user=request.user).count() == 0:
        customer_key = hashlib.md5(
            (str(uuid.uuid4()) + str(request.user) + str(uuid.uuid4())).encode()
        ).hexdigest()
        while await UsersPaymentClient.filter(customer_key=customer_key).count() > 0:
            customer_key = hashlib.md5(
                str(uuid.uuid4()) + request.user + str(uuid.uuid4())
            ).hexdigest()
        client = {
            "TerminalKey": terminal_key,
            "CustomerKey": customer_key,
            "Email": item.email,
            "Phone": item.phone,
            "Token": token,
        }
        new_client = requests.post(
            "https://securepay.tinkoff.ru/v2/AddCustomer",  # Регистрирует клиента в связке с терминалом.
            json=client,
            headers=content_type,
        )
        if new_client.json()["Success"] is True:
            await UsersPaymentClient.create(
                id_user=request.user, customer_key=customer_key
            )
        else:
            return access_forbidden
    client = await UsersPaymentClient.filter(id_user=request.user).first().values()
    data = {
        "TerminalKey": terminal_key,
        "Amount": item.amount,
        "OrderId": order_id,
        "CustomerKey": client["CustomerKey"],
        "Description": "Пополнение баланса аккаунта Няня Го",
        "Recurrent": item.recurrent,
        "PayType": "O",
        "SuccessURL": f"https://nynyago.ru/api/v1.0/payments/payments_success?order_id={order_id}",
        "NotificationURL": f"https://nynyago.ru/api/v1.0/payments/payments_status/{order_id}",
        "FailURL": "https://nynyago.ru/api/v1.0/payments/payments_unsuccessful?order_id={order_id}",
        "DATA": {
            "Phone": item.phone,
            "Email": item.email,
            "TinkoffPayWeb": "true",
            "Device": "Mobile",
            "DeviceOs": "Android",
            "DeviceWebView": "true",
            "DeviceBrowser": "Chrome",
        },
    }
    init_data = requests.post(
        "https://securepay.tinkoff.ru/v2/Init", json=data, headers=content_type
    ).json()
    if init_data["Success"] is False:
        print(init_data)
        raise HTTPException(505, detail=init_data)
    check_data = {
        "PaymentId": init_data["PaymentId"],
        "TerminalKey": terminal_key,
        "CardData": item.card_data,
        "Token": hashlib.sha256(
            f"{item.amount}{password}{init_data['PaymentId']}{terminal_key}".encode()
        ).hexdigest(),
    }
    check_3ds_data = requests.post(
        "https://securepay.tinkoff.ru/v2/Check3dsVersion",
        json=check_data,
        headers=content_type,
    ).json()
    if item.ip is None:
        item.ip = "02a3:06f0:0004:0000:0000:0000:0000:0edf"
    if check_3ds_data["Success"] is False:
        print(check_3ds_data)
        raise HTTPException(506, detail=check_3ds_data)
    if check_3ds_data["Version"] == "2.1.0":
        await WaitDataPaymentTink.create(
            id_user=request.user,
            id_payment=init_data["PaymentId"],
            id_order=order_id,
            card_data=item.card_data,
            ip=item.ip,
            amount=item.amount,
            token=hashlib.sha256(
                f"{item.amount}{password}{init_data['PaymentId']}"
                f"{terminal_key}".encode()
            ).hexdigest(),
            TdsServerTransID=check_3ds_data["TdsServerTransID"],
        )
        return JSONResponse(
            {
                "is3DsVersion2": True,
                "TerminalKey": terminal_key,
                "PaymentId": init_data["PaymentId"],
                "serverTransId": check_3ds_data["TdsServerTransID"],
                "ThreeDSMethodURL": check_3ds_data["ThreeDSMethodURL"],
            }
        )
    confirm_payment = {
        "PaymentId": init_data["PaymentId"],
        "TerminalKey": terminal_key,
        "Token": hashlib.sha256(
            f"{item.amount}{password}{init_data['PaymentId']}{terminal_key}".encode()
        ).hexdigest(),
        "IP": item.ip,
        "CardData": item.card_data,
        "Amount": item.amount,
        "deviceChannel": "02",
    }
    if item.email is not None and len(item.email) > 0:
        confirm_payment["SendEmail"] = True
        confirm_payment["InfoEmail"] = item.email
    confirm_payment_data = requests.post(
        "https://securepay.tinkoff.ru/v2/FinishAuthorize",
        json=confirm_payment,
        headers=content_type,
    ).json()
    token = hashlib.sha256(
        f"{item.amount}{password}{init_data['PaymentId']}{terminal_key}".encode()
    ).hexdigest()
    await HistoryPaymentTink.create(
        id_order=order_id,
        amount=item.amount,
        id_user=request.user,
        ip=item.ip,
        card_data=item.card_data,
        token=token,
        id_payment=init_data["PaymentId"],
    )
    if confirm_payment_data["Success"] is False:
        print(confirm_payment_data)
        raise HTTPException(507, detail=confirm_payment_data)
    return JSONResponse(
        {
            "status": True,
            "message": "Success!",
            "is3DsVersion2": (
                True
                if check_3ds_data["Version"] == "2.1.0"
                else False if check_3ds_data["Version"] == "1.0.0" else None
            ),
            "serverTransId": (
                check_3ds_data["TdsServerTransID"]
                if "TdsServerTransID" in check_3ds_data
                and check_3ds_data["TdsServerTransID"] is not None
                else None
            ),
            "acsUrl": confirm_payment_data["ACSUrl"],
            "md": confirm_payment_data["MD"],
            "paReq": confirm_payment_data["PaReq"],
            "TerminalKey": terminal_key,
            "acsTransId": (
                None
                if "AcsTransId" not in confirm_payment_data
                or confirm_payment_data["AcsTransId"] is None
                else confirm_payment_data["AcsTransId"]
            ),
        }
    )


@router.post("/add_child")
async def add_child(request: Request, payload: ChildCreate):
    # Проверка доступа через сервис
    is_parent = await UserService.check_user_role(request.user, 1)
    is_admin = await UserService.check_user_role(request.user, 6) or await UserService.check_user_role(request.user, 7)
    
    if not is_parent and not is_admin:
        return access_forbidden
    
    # Определяем ID пользователя для ребенка
    target_user_id = request.user
    if is_admin and payload.id_user:
        target_user_id = payload.id_user
    elif is_admin and not payload.id_user:
        return {"error": "id_user is required for admin"}
    
    # Создаем ребенка через сервис
    child_id = await UserService.add_child(
        user_id=target_user_id,
        child_data={
            "surname": payload.surname,
            "name": payload.name,
            "patronymic": payload.patronymic,
            "child_phone": payload.child_phone,
            "age": payload.age
        }
    )
    
    if child_id:
        return {"status": "ok", "child_id": child_id}
    return access_forbidden


@router.put("/update_child/{child_id}")
async def update_child(request: Request, child_id: int, payload: ChildUpdate):
    # Обновляем ребенка через сервис
    success = await UserService.update_child(
        user_id=request.user,
        child_id=child_id,
        update_data=payload.dict(exclude_unset=True)
    )
    
    if success:
        return {"status": "ok"}
    return {"error": "child not found or access denied"}


@router.delete("/delete_child/{child_id}")
async def delete_child(request: Request, child_id: int):
    # Удаляем ребенка через сервис
    success = await UserService.delete_child(
        user_id=request.user,
        child_id=child_id
    )
    
    if success:
        return {"status": "ok"}
    return {"error": "child not found or access denied"}


@router.get("/children")
async def get_my_children(request: Request):
    """
    Получить список детей текущего пользователя.
    BE-MVP-016: CRUD API профилей детей
    
    Returns:
        JSONResponse: Список детей с полной информацией
    """
    children = await UserService.get_user_children(request.user)
    return JSONResponse({
        "status": True,
        "message": "Success!",
        "children": children,
        "total": len(children)
    })


@router.get("/get_me_extended")
async def get_extended_client_info(request: Request):
    """
    Получить расширенную информацию о пользователе:
        - Информация о родителе
        - Информация о детях (с привязанными локациями)
        - Локации без привязки к детям

    Args:
        request (Request): Запрос.

    Returns:
        JSONResponse: Ответ в формате JSON с полной информацией о пользователе.
    """
    # Проверяем существование пользователя
    if not await UsersUser.filter(id=request.user, isActive=True).exists():
        return JSONResponse(
            {"status": False, "message": "User not found or inactive"},
            status_code=404
        )

    user_info = await UsersUser.filter(id=request.user).first().values(
        "id",
        "name",
        "surname",
        "phone",
    )

    children = await UsersChild.filter(
        id_user=request.user,
        isActive=True
    ).order_by("-datetime_create").values(
        "id",
        "surname",
        "name",
        "patronymic",
        "child_phone",
        "age",
    )

    user_photopath = await UsersUserPhoto.filter(id_user=request.user).first().values(
        "photo_path")
    user_info["photo_path"] = user_photopath[
        "photo_path"] if user_photopath is not None and "photo_path" in user_photopath else not_user_photo

    # =================== Получаем инфо о локациях ===================
    user_schedules = await DataSchedule.filter(
        id_user=request.user,
        isActive__in=[True, False]
    ).all().values_list("id", flat=True)

    # Получаем все активные маршруты с основной информацией
    roads = await DataScheduleRoad.filter(
        isActive=True,
        id_schedule__in=list(user_schedules)
    ).all().values(
        "id", "title", "week_day", "start_time", "end_time", "type_drive"
    )

    # Получаем все связи маршрутов с детьми
    road_child_relations = await DataScheduleRoadChild.filter(
        id_schedule_road__in=[road["id"] for road in roads],
        isActive=True
    ).all().values(
        "id_schedule_road", "id_child"
    )

    # Создаем словарь для группировки локаций по детям
    children_locations = {child["id"]: [] for child in children}
    unassigned_locations_dict = {}  # Будем использовать словарь для группировки по адресам
    processed_roads = set()

    for road in roads:
        # Получаем адреса для маршрута
        addresses = await DataScheduleRoadAddress.filter(
            id_schedule_road=road["id"]
        ).order_by("id").all().values(
            "from_address", "to_address", "from_lon", "from_lat", "to_lon", "to_lat"
        )

        # Получаем контактные лица для маршрута
        contacts = await DataScheduleRoadContact.filter(
            id_schedule_road=road["id"], isActive=True
        ).all().values(
            "surname", "name", "patronymic", "contact_phone"
        )

        # Формируем ФИО контактного лица
        contact_info = None
        if contacts:
            contact = contacts[0]  # Берем первое контактное лицо
            contact_info = {
                "fio": f"{contact['surname'] or ''} {contact['name'] or ''} {contact['patronymic'] or ''}".strip(),
                "phone": contact["contact_phone"]
            }

        # Создаем ключ для группировки локаций по адресам
        location_key_parts = []
        intermediate_points = []

        if addresses:
            if "2" in road["type_drive"]:
                # Для сложных маршрутов
                points = []
                for addr in addresses:
                    points.append({
                        "address": addr["from_address"],
                        "lon": addr["from_lon"],
                        "lat": addr["from_lat"]
                    })
                    if addr == addresses[-1]:
                        points.append({
                            "address": addr["to_address"],
                            "lon": addr["to_lon"],
                            "lat": addr["to_lat"]
                        })

                from_point = points[0]
                to_point = points[-1]
                intermediate_points = points[1:-1] if len(points) > 2 else []

                location_key_parts.extend([
                    f"from:{from_point['address']}_{from_point['lon']}_{from_point['lat']}",
                    f"to:{to_point['address']}_{to_point['lon']}_{to_point['lat']}"
                ])

                for i, point in enumerate(intermediate_points):
                    location_key_parts.append(
                        f"int_{i}:{point['address']}_{point['lon']}_{point['lat']}")
            else:
                # Для простых маршрутов
                addr = addresses[0]
                location_key_parts.extend([
                    f"from:{addr['from_address']}_{addr['from_lon']}_{addr['from_lat']}",
                    f"to:{addr['to_address']}_{addr['to_lon']}_{addr['to_lat']}"
                ])
                from_point = {
                    "address": addr["from_address"],
                    "lon": addr["from_lon"],
                    "lat": addr["from_lat"]
                }
                to_point = {
                    "address": addr["to_address"],
                    "lon": addr["to_lon"],
                    "lat": addr["to_lat"]
                }

        location_key = "|".join(location_key_parts)

        # Создаем объект локации
        location = {
            "road_id": road["id"],
            "name": road["title"],
            "contact": contact_info,
            "schedule": {
                "week_day": road["week_day"],
                "start_time": road["start_time"],
                "end_time": road["end_time"]
            },
            "is_complex": "2" in road["type_drive"],
            "from_address": from_point["address"] if addresses else None,
            "to_address": to_point["address"] if addresses else None,
            "from_lon": from_point["lon"] if addresses else None,
            "from_lat": from_point["lat"] if addresses else None,
            "to_lon": to_point["lon"] if addresses else None,
            "to_lat": to_point["lat"] if addresses else None,
            "intermediate_points": intermediate_points
        }

        # Находим детей, связанных с этим маршрутом
        related_children = [rel["id_child"] for rel in road_child_relations if
                            rel["id_schedule_road"] == road["id"]]

        if related_children:
            # Добавляем локацию к каждому связанному ребенку
            for child_id in related_children:
                if child_id in children_locations:
                    # Проверяем, есть ли уже такая локация у ребенка
                    existing_loc_index = None
                    for i, loc in enumerate(children_locations[child_id]):
                        existing_key_parts = []
                        existing_key_parts.extend([
                            f"from:{loc['from_address']}_{loc['from_lon']}_{loc['from_lat']}",
                            f"to:{loc['to_address']}_{loc['to_lon']}_{loc['to_lat']}"
                        ])
                        for j, point in enumerate(loc.get("intermediate_points", [])):
                            existing_key_parts.append(
                                f"int_{j}:{point['address']}_{point['lon']}_{point['lat']}")
                        existing_key = "|".join(existing_key_parts)

                        if existing_key == location_key:
                            existing_loc_index = i
                            break

                    if existing_loc_index is not None:
                        # Добавляем расписание к существующей локации
                        children_locations[child_id][existing_loc_index][
                            "schedules"].append(location["schedule"])
                    else:
                        # Создаем новую локацию с массивом расписаний
                        new_location = {
                            "road_id": location["road_id"],
                            "name": location["name"],
                            "contact": location["contact"],
                            "schedules": [location["schedule"]],
                            "is_complex": location["is_complex"],
                            "from_address": location["from_address"],
                            "to_address": location["to_address"],
                            "from_lon": location["from_lon"],
                            "from_lat": location["from_lat"],
                            "to_lon": location["to_lon"],
                            "to_lat": location["to_lat"],
                            "intermediate_points": location["intermediate_points"]
                        }
                        children_locations[child_id].append(new_location)
        else:
            # Локация без привязки к детям
            if location_key in unassigned_locations_dict:
                # Добавляем расписание к существующей локации
                unassigned_locations_dict[location_key]["schedules"].append(
                    location["schedule"])
                # Обновляем road_ids (можно добавить или заменить)
                if isinstance(unassigned_locations_dict[location_key]["road_id"], list):
                    unassigned_locations_dict[location_key]["road_id"].append(
                        location["road_id"])
                else:
                    unassigned_locations_dict[location_key]["road_id"] = [
                        unassigned_locations_dict[location_key]["road_id"],
                        location["road_id"]]
            else:
                # Создаем новую локацию с массивом расписаний
                new_location = {
                    "road_id": location["road_id"],
                    "name": location["name"],
                    "contact": location["contact"],
                    "schedules": [location["schedule"]],
                    "is_complex": location["is_complex"],
                    "from_address": location["from_address"],
                    "to_address": location["to_address"],
                    "from_lon": location["from_lon"],
                    "from_lat": location["from_lat"],
                    "to_lon": location["to_lon"],
                    "to_lat": location["to_lat"],
                    "intermediate_points": location["intermediate_points"]
                }
                unassigned_locations_dict[location_key] = new_location

    # Формируем итоговый список детей с их локациями
    children_with_locations = []
    for child in children:
        child_data = dict(child)
        child_data["locations"] = children_locations.get(child["id"], [])
        children_with_locations.append(child_data)

    # Конвертируем словарь несвязанных локаций в список
    unassigned_locations = list(unassigned_locations_dict.values())

    return JSONResponse({
        "success": True,
        "user": user_info,
        "children": children_with_locations,
        "unassigned_locations": unassigned_locations,
    })


@router.post("/activate_sos", responses=generate_responses([success_answer]))
async def activate_sos(request: Request, item: SOSActivate):
    """
    BE-MVP-020: Активация SOS-кнопки.
    
    Создает запись о SOS-событии, отправляет уведомления:
    - Всем администраторам (id_type_account=3)
    - Экстренным контактам (если будут реализованы в BE-MVP-018)
    
    Args:
        request: Объект запроса с user ID
        item: Данные SOS (GPS координаты, сообщение, id заказа)
        
    Returns:
        JSONResponse: Статус операции и ID созданного SOS-события
    """
    try:
        # Создаем запись SOS-события
        sos_event = await SOSEvent.create(
            id_user=request.user,
            id_order=item.id_order,
            latitude=item.latitude,
            longitude=item.longitude,
            message=item.message,
            status='active'
        )
        
        # Получаем информацию о пользователе
        user = await UsersUser.filter(id=request.user).first().values()
        user_name = f"{user.get('name', '')} {user.get('surname', '')}".strip() or "Пользователь"
        
        # Формируем текст уведомления
        location_text = ""
        if item.latitude and item.longitude:
            location_text = f"\nКоординаты: {item.latitude}, {item.longitude}"
            location_text += f"\nGoogle Maps: https://maps.google.com/?q={item.latitude},{item.longitude}"
        
        message_text = f"\n\nСообщение: {item.message}" if item.message else ""
        order_text = f"\nЗаказ ID: {item.id_order}" if item.id_order else ""
        
        notification_body = (
            f"🆘 SOS от пользователя {user_name} (ID: {request.user})"
            f"{order_text}"
            f"{location_text}"
            f"{message_text}"
        )
        
        # Логируем событие
        logger.critical(
            f"SOS activated by user {request.user}",
            extra={
                "user_id": request.user,
                "sos_event_id": sos_event.id,
                "latitude": item.latitude,
                "longitude": item.longitude,
                "order_id": item.id_order,
                "message": item.message,
                "event_type": "sos_activated"
            }
        )
        
        # Получаем всех администраторов
        admin_accounts = await UsersUserAccount.filter(id_type_account=3).all().values("id_user")
        admin_ids = [acc["id_user"] for acc in admin_accounts]
        
        # Отправляем уведомления всем администраторам
        notifications_sent = 0
        for admin_id in admin_ids:
            try:
                # Получаем Firebase token администратора
                fbid = await UsersBearerToken.filter(id_user=admin_id).order_by("-id").first()
                
                if fbid:
                    await sendPush(
                        fbid.fbid,
                        "🆘 ЭКСТРЕННЫЙ ВЫЗОВ SOS",
                        f"SOS от {user_name}. Требуется немедленная помощь!",
                        {
                            "action": "sos_alert",
                            "sos_event_id": str(sos_event.id),
                            "user_id": str(request.user),
                            "latitude": str(item.latitude) if item.latitude else "",
                            "longitude": str(item.longitude) if item.longitude else "",
                            "order_id": str(item.id_order) if item.id_order else ""
                        }
                    )
                    
                    # Сохраняем в историю уведомлений
                    await HistoryNotification.create(
                        id_user=admin_id,
                        title="🆘 ЭКСТРЕННЫЙ ВЫЗОВ SOS",
                        description=notification_body
                    )
                    
                    notifications_sent += 1
                    
                    logger.info(
                        f"SOS notification sent to admin {admin_id}",
                        extra={
                            "admin_id": admin_id,
                            "sos_event_id": sos_event.id,
                            "event_type": "sos_notification_sent"
                        }
                    )
            except Exception as e:
                logger.error(
                    f"Failed to send SOS notification to admin {admin_id}: {str(e)}",
                    extra={
                        "admin_id": admin_id,
                        "sos_event_id": sos_event.id,
                        "error": str(e),
                        "event_type": "sos_notification_failed"
                    }
                )
        
        # BE-MVP-018: Отправить уведомления экстренным контактам детей
        emergency_notifications_sent = 0
        if item.id_order:
            try:
                # Получаем детей, связанных с заказом
                order_children = await DataScheduleRoadChild.filter(
                    id_road__in=(
                        await DataScheduleRoad.filter(
                            id_schedule__in=(
                                await DataSchedule.filter(id=item.id_order).values_list("id", flat=True)
                            )
                        ).values_list("id", flat=True)
                    )
                ).values_list("id_child", flat=True)
                
                # Получаем экстренные контакты для этих детей
                emergency_contacts = await ChildEmergencyContact.filter(
                    id_child__in=order_children,
                    isActive=True
                ).order_by("priority").all().values()
                
                # Отправляем SMS/уведомления экстренным контактам
                for contact in emergency_contacts:
                    try:
                        # TODO: Интеграция с SMS-сервисом для отправки SMS
                        # Пока только логируем
                        logger.warning(
                            f"Emergency contact notified about SOS",
                            extra={
                                "contact_id": contact["id"],
                                "contact_name": contact["name"],
                                "contact_phone": contact["phone"],
                                "relationship": contact["relationship"],
                                "sos_event_id": sos_event.id,
                                "event_type": "emergency_contact_notified"
                            }
                        )
                        emergency_notifications_sent += 1
                    except Exception as e:
                        logger.error(
                            f"Failed to notify emergency contact {contact['id']}: {str(e)}",
                            extra={
                                "contact_id": contact["id"],
                                "sos_event_id": sos_event.id,
                                "error": str(e),
                                "event_type": "emergency_contact_notification_failed"
                            }
                        )
            except Exception as e:
                logger.error(
                    f"Error processing emergency contacts for SOS: {str(e)}",
                    extra={
                        "sos_event_id": sos_event.id,
                        "error": str(e),
                        "event_type": "emergency_contacts_processing_error"
                    }
                )
        
        logger.info(
            f"SOS event created successfully. Notifications sent: {notifications_sent + emergency_notifications_sent}",
            extra={
                "sos_event_id": sos_event.id,
                "admin_notifications_sent": notifications_sent,
                "emergency_notifications_sent": emergency_notifications_sent,
                "total_notifications": notifications_sent + emergency_notifications_sent,
                "admins_count": len(admin_ids),
                "event_type": "sos_completed"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "SOS активирован. Помощь уже в пути!",
            "sos_event_id": sos_event.id,
            "admin_notifications_sent": notifications_sent,
            "emergency_notifications_sent": emergency_notifications_sent,
            "total_notifications_sent": notifications_sent + emergency_notifications_sent
        })
        
    except Exception as e:
        logger.error(
            f"Error activating SOS: {str(e)}",
            extra={
                "user_id": request.user,
                "error": str(e),
                "event_type": "sos_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка активации SOS. Попробуйте еще раз или позвоните в службу спасения."
        }, 500)


@router.post("/emergency_contacts", responses=generate_responses([success_answer]))
async def create_emergency_contact(request: Request, item: EmergencyContactCreate):
    """
    BE-MVP-018: Создание экстренного контакта для ребенка.
    
    Args:
        request: Объект запроса с user ID
        item: Данные контакта (имя, родство, телефон, приоритет)
        
    Returns:
        JSONResponse: Статус операции и ID созданного контакта
    """
    try:
        # Проверяем, что ребенок принадлежит текущему пользователю
        child = await UsersChild.filter(id=item.id_child, id_user=request.user, isActive=True).first()
        
        if not child:
            return JSONResponse({
                "status": False,
                "message": "Ребенок не найден или не принадлежит вам"
            }, 404)
        
        # Создаем экстренный контакт
        contact = await ChildEmergencyContact.create(
            id_child=item.id_child,
            name=item.name,
            relationship=item.relationship,
            phone=item.phone,
            priority=item.priority or 1,
            notes=item.notes
        )
        
        logger.info(
            f"Emergency contact created for child {item.id_child}",
            extra={
                "user_id": request.user,
                "child_id": item.id_child,
                "contact_id": contact.id,
                "relationship": item.relationship,
                "event_type": "emergency_contact_created"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Экстренный контакт успешно добавлен",
            "contact_id": contact.id
        })
        
    except Exception as e:
        logger.error(
            f"Error creating emergency contact: {str(e)}",
            extra={
                "user_id": request.user,
                "child_id": item.id_child,
                "error": str(e),
                "event_type": "emergency_contact_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при создании экстренного контакта"
        }, 500)


@router.get("/emergency_contacts/{child_id}")
async def get_emergency_contacts(request: Request, child_id: int):
    """
    BE-MVP-018: Получение списка экстренных контактов ребенка.
    
    Args:
        request: Объект запроса с user ID
        child_id: ID ребенка
        
    Returns:
        JSONResponse: Список экстренных контактов
    """
    try:
        # Проверяем, что ребенок принадлежит текущему пользователю
        child = await UsersChild.filter(id=child_id, id_user=request.user, isActive=True).first()
        
        if not child:
            return JSONResponse({
                "status": False,
                "message": "Ребенок не найден или не принадлежит вам"
            }, 404)
        
        # Получаем все активные контакты, отсортированные по приоритету
        contacts = await ChildEmergencyContact.filter(
            id_child=child_id,
            isActive=True
        ).order_by("priority").all().values()
        
        return JSONResponse({
            "status": True,
            "contacts": contacts,
            "total": len(contacts)
        })
        
    except Exception as e:
        logger.error(
            f"Error getting emergency contacts: {str(e)}",
            extra={
                "user_id": request.user,
                "child_id": child_id,
                "error": str(e),
                "event_type": "emergency_contact_get_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при получении экстренных контактов"
        }, 500)


@router.put("/emergency_contacts/{contact_id}")
async def update_emergency_contact(request: Request, contact_id: int, item: EmergencyContactUpdate):
    """
    BE-MVP-018: Обновление экстренного контакта.
    
    Args:
        request: Объект запроса с user ID
        contact_id: ID контакта
        item: Данные для обновления
        
    Returns:
        JSONResponse: Статус операции
    """
    try:
        # Получаем контакт
        contact = await ChildEmergencyContact.filter(id=contact_id, isActive=True).first()
        
        if not contact:
            return JSONResponse({
                "status": False,
                "message": "Экстренный контакт не найден"
            }, 404)
        
        # Проверяем, что ребенок принадлежит текущему пользователю
        child = await UsersChild.filter(id=contact.id_child, id_user=request.user, isActive=True).first()
        
        if not child:
            return JSONResponse({
                "status": False,
                "message": "Нет доступа к этому контакту"
            }, 403)
        
        # Обновляем поля
        update_data = {}
        if item.name is not None:
            update_data["name"] = item.name
        if item.relationship is not None:
            update_data["relationship"] = item.relationship
        if item.phone is not None:
            update_data["phone"] = item.phone
        if item.priority is not None:
            update_data["priority"] = item.priority
        if item.notes is not None:
            update_data["notes"] = item.notes
        if item.is_active is not None:
            update_data["isActive"] = item.is_active
        
        if update_data:
            await ChildEmergencyContact.filter(id=contact_id).update(**update_data)
            
            logger.info(
                f"Emergency contact {contact_id} updated",
                extra={
                    "user_id": request.user,
                    "contact_id": contact_id,
                    "child_id": contact.id_child,
                    "updated_fields": list(update_data.keys()),
                    "event_type": "emergency_contact_updated"
                }
            )
        
        return JSONResponse({
            "status": True,
            "message": "Экстренный контакт успешно обновлен"
        })
        
    except Exception as e:
        logger.error(
            f"Error updating emergency contact: {str(e)}",
            extra={
                "user_id": request.user,
                "contact_id": contact_id,
                "error": str(e),
                "event_type": "emergency_contact_update_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при обновлении экстренного контакта"
        }, 500)


@router.delete("/emergency_contacts/{contact_id}")
async def delete_emergency_contact(request: Request, contact_id: int):
    """
    BE-MVP-018: Удаление (деактивация) экстренного контакта.
    
    Args:
        request: Объект запроса с user ID
        contact_id: ID контакта
        
    Returns:
        JSONResponse: Статус операции
    """
    try:
        # Получаем контакт
        contact = await ChildEmergencyContact.filter(id=contact_id, isActive=True).first()
        
        if not contact:
            return JSONResponse({
                "status": False,
                "message": "Экстренный контакт не найден"
            }, 404)
        
        # Проверяем, что ребенок принадлежит текущему пользователю
        child = await UsersChild.filter(id=contact.id_child, id_user=request.user, isActive=True).first()
        
        if not child:
            return JSONResponse({
                "status": False,
                "message": "Нет доступа к этому контакту"
            }, 403)
        
        # Деактивируем контакт (мягкое удаление)
        await ChildEmergencyContact.filter(id=contact_id).update(isActive=False)
        
        logger.info(
            f"Emergency contact {contact_id} deleted",
            extra={
                "user_id": request.user,
                "contact_id": contact_id,
                "child_id": contact.id_child,
                "event_type": "emergency_contact_deleted"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Экстренный контакт успешно удален"
        })
        
    except Exception as e:
        logger.error(
            f"Error deleting emergency contact: {str(e)}",
            extra={
                "user_id": request.user,
                "contact_id": contact_id,
                "error": str(e),
                "event_type": "emergency_contact_delete_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при удалении экстренного контакта"
        }, 500)


# ============================================================================
# BE-MVP-017: Медицинская информация детей
# ============================================================================

@router.post("/medical_info", responses=generate_responses([success_answer]))
async def create_medical_info(request: Request, item: MedicalInfoCreate):
    """
    BE-MVP-017: Создание медицинской информации для ребенка.
    
    Args:
        request: Объект запроса с user ID
        item: Данные медицинской информации
        
    Returns:
        JSONResponse: Статус операции и ID созданной записи
    """
    try:
        # Проверяем, что ребенок принадлежит текущему пользователю
        child = await UsersChild.filter(id=item.id_child, id_user=request.user, isActive=True).first()
        
        if not child:
            return JSONResponse({
                "status": False,
                "message": "Ребенок не найден или не принадлежит вам"
            }, 404)
        
        # Проверяем, нет ли уже медицинской информации для этого ребенка
        existing = await ChildMedicalInfo.filter(id_child=item.id_child, isActive=True).first()
        if existing:
            return JSONResponse({
                "status": False,
                "message": "Медицинская информация для этого ребенка уже существует. Используйте PUT для обновления."
            }, 400)
        
        # Создаем медицинскую информацию
        from datetime import datetime
        medical_info = await ChildMedicalInfo.create(
            id_child=item.id_child,
            allergies=item.allergies,
            chronic_diseases=item.chronic_diseases,
            medications=item.medications,
            medical_policy_number=item.medical_policy_number,
            blood_type=item.blood_type,
            special_needs=item.special_needs,
            doctor_notes=item.doctor_notes,
            datetime_create=datetime.now()
        )
        
        logger.info(
            f"Medical info created for child {item.id_child}",
            extra={
                "user_id": request.user,
                "child_id": item.id_child,
                "medical_info_id": medical_info.id,
                "has_allergies": bool(item.allergies),
                "has_chronic_diseases": bool(item.chronic_diseases),
                "event_type": "medical_info_created"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Медицинская информация успешно добавлена",
            "medical_info_id": medical_info.id
        })
        
    except Exception as e:
        logger.error(
            f"Error creating medical info: {str(e)}",
            extra={
                "user_id": request.user,
                "child_id": item.id_child,
                "error": str(e),
                "event_type": "medical_info_create_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при создании медицинской информации"
        }, 500)


@router.get("/medical_info/{child_id}")
async def get_medical_info(request: Request, child_id: int):
    """
    BE-MVP-017: Получение медицинской информации ребенка.
    
    Args:
        request: Объект запроса с user ID
        child_id: ID ребенка
        
    Returns:
        JSONResponse: Медицинская информация ребенка
    """
    try:
        # Проверяем, что ребенок принадлежит текущему пользователю
        child = await UsersChild.filter(id=child_id, id_user=request.user, isActive=True).first()
        
        if not child:
            return JSONResponse({
                "status": False,
                "message": "Ребенок не найден или не принадлежит вам"
            }, 404)
        
        # Получаем медицинскую информацию
        medical_info = await ChildMedicalInfo.filter(
            id_child=child_id,
            isActive=True
        ).first()
        
        if not medical_info:
            return JSONResponse({
                "status": True,
                "message": "Медицинская информация не найдена",
                "medical_info": None
            })
        
        medical_data = {
            "id": medical_info.id,
            "id_child": medical_info.id_child,
            "allergies": medical_info.allergies,
            "chronic_diseases": medical_info.chronic_diseases,
            "medications": medical_info.medications,
            "medical_policy_number": medical_info.medical_policy_number,
            "blood_type": medical_info.blood_type,
            "special_needs": medical_info.special_needs,
            "doctor_notes": medical_info.doctor_notes,
            "policy_document_path": medical_info.policy_document_path,
            "medical_certificate_path": medical_info.medical_certificate_path,
            "datetime_create": await get_date_from_datetime(medical_info.datetime_create) if medical_info.datetime_create else None,
            "datetime_update": await get_date_from_datetime(medical_info.datetime_update) if medical_info.datetime_update else None
        }
        
        return JSONResponse({
            "status": True,
            "message": "Success",
            "medical_info": medical_data
        })
        
    except Exception as e:
        logger.error(
            f"Error getting medical info: {str(e)}",
            extra={
                "user_id": request.user,
                "child_id": child_id,
                "error": str(e),
                "event_type": "medical_info_get_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при получении медицинской информации"
        }, 500)


@router.put("/medical_info/{child_id}")
async def update_medical_info(request: Request, child_id: int, item: MedicalInfoUpdate):
    """
    BE-MVP-017: Обновление медицинской информации ребенка.
    
    Args:
        request: Объект запроса с user ID
        child_id: ID ребенка
        item: Данные для обновления
        
    Returns:
        JSONResponse: Статус операции
    """
    try:
        # Проверяем, что ребенок принадлежит текущему пользователю
        child = await UsersChild.filter(id=child_id, id_user=request.user, isActive=True).first()
        
        if not child:
            return JSONResponse({
                "status": False,
                "message": "Ребенок не найден или не принадлежит вам"
            }, 404)
        
        # Получаем медицинскую информацию
        medical_info = await ChildMedicalInfo.filter(id_child=child_id, isActive=True).first()
        
        if not medical_info:
            return JSONResponse({
                "status": False,
                "message": "Медицинская информация не найдена. Используйте POST для создания."
            }, 404)
        
        # Обновляем поля
        update_data = {}
        if item.allergies is not None:
            update_data["allergies"] = item.allergies
        if item.chronic_diseases is not None:
            update_data["chronic_diseases"] = item.chronic_diseases
        if item.medications is not None:
            update_data["medications"] = item.medications
        if item.medical_policy_number is not None:
            update_data["medical_policy_number"] = item.medical_policy_number
        if item.blood_type is not None:
            update_data["blood_type"] = item.blood_type
        if item.special_needs is not None:
            update_data["special_needs"] = item.special_needs
        if item.doctor_notes is not None:
            update_data["doctor_notes"] = item.doctor_notes
        if item.is_active is not None:
            update_data["isActive"] = item.is_active
        
        if update_data:
            from datetime import datetime
            update_data["datetime_update"] = datetime.now()
            await ChildMedicalInfo.filter(id=medical_info.id).update(**update_data)
            
            logger.info(
                f"Medical info {medical_info.id} updated",
                extra={
                    "user_id": request.user,
                    "medical_info_id": medical_info.id,
                    "child_id": child_id,
                    "updated_fields": list(update_data.keys()),
                    "event_type": "medical_info_updated"
                }
            )
        
        return JSONResponse({
            "status": True,
            "message": "Медицинская информация успешно обновлена"
        })
        
    except Exception as e:
        logger.error(
            f"Error updating medical info: {str(e)}",
            extra={
                "user_id": request.user,
                "child_id": child_id,
                "error": str(e),
                "event_type": "medical_info_update_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при обновлении медицинской информации"
        }, 500)


@router.delete("/medical_info/{child_id}")
async def delete_medical_info(request: Request, child_id: int):
    """
    BE-MVP-017: Удаление (деактивация) медицинской информации ребенка.
    
    Args:
        request: Объект запроса с user ID
        child_id: ID ребенка
        
    Returns:
        JSONResponse: Статус операции
    """
    try:
        # Проверяем, что ребенок принадлежит текущему пользователю
        child = await UsersChild.filter(id=child_id, id_user=request.user, isActive=True).first()
        
        if not child:
            return JSONResponse({
                "status": False,
                "message": "Ребенок не найден или не принадлежит вам"
            }, 404)
        
        # Получаем медицинскую информацию
        medical_info = await ChildMedicalInfo.filter(id_child=child_id, isActive=True).first()
        
        if not medical_info:
            return JSONResponse({
                "status": False,
                "message": "Медицинская информация не найдена"
            }, 404)
        
        # Деактивируем медицинскую информацию (мягкое удаление)
        await ChildMedicalInfo.filter(id=medical_info.id).update(isActive=False)
        
        logger.info(
            f"Medical info {medical_info.id} deleted",
            extra={
                "user_id": request.user,
                "medical_info_id": medical_info.id,
                "child_id": child_id,
                "event_type": "medical_info_deleted"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Медицинская информация успешно удалена"
        })
        
    except Exception as e:
        logger.error(
            f"Error deleting medical info: {str(e)}",
            extra={
                "user_id": request.user,
                "child_id": child_id,
                "error": str(e),
                "event_type": "medical_info_delete_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при удалении медицинской информации"
        }, 500)


# ============================================================================
# BE-MVP-021: Верификация водителя (родительская сторона)
# ============================================================================

@router.post("/verify_driver", responses=generate_responses([success_answer]))
async def verify_driver_by_parent(request: Request, item: VerifyMeetingCode):
    """
    BE-MVP-021: Верификация водителя родителем через код встречи.
    
    Родитель вводит 4-значный код, который показал водитель,
    чтобы подтвердить личность водителя при передаче ребенка.
    
    Args:
        request: Объект запроса с parent ID
        item: Код встречи и ID маршрута
        
    Returns:
        JSONResponse: Результат верификации с информацией о водителе
    """
    try:
        from datetime import datetime
        
        # Проверяем, что родитель имеет отношение к этому маршруту
        road = await DataScheduleRoad.filter(id=item.id_schedule_road).first()
        if not road:
            return JSONResponse({
                "status": False,
                "message": "Маршрут не найден"
            }, 404)
        
        schedule = await DataSchedule.filter(id=road.id_schedule).first()
        if not schedule or schedule.id_user != request.user:
            return JSONResponse({
                "status": False,
                "message": "У вас нет доступа к этому маршруту"
            }, 403)
        
        # Ищем код встречи
        code_record = await DriverMeetingCode.filter(
            meeting_code=item.meeting_code,
            id_schedule_road=item.id_schedule_road,
            isActive=True
        ).first()
        
        if not code_record:
            logger.warning(
                f"Parent {request.user} entered invalid meeting code",
                extra={
                    "parent_id": request.user,
                    "road_id": item.id_schedule_road,
                    "entered_code": item.meeting_code,
                    "event_type": "parent_meeting_code_invalid"
                }
            )
            return JSONResponse({
                "status": False,
                "message": "Неверный код встречи. Проверьте код и попробуйте снова."
            }, 400)
        
        # Проверяем, не истек ли код
        if code_record.expires_at < datetime.now():
            return JSONResponse({
                "status": False,
                "message": "Код встречи истек. Попросите водителя сгенерировать новый код."
            }, 400)
        
        # Проверяем, не был ли код уже использован
        if code_record.is_used:
            return JSONResponse({
                "status": False,
                "message": "Этот код уже был использован ранее"
            }, 400)
        
        # Помечаем код как использованный
        await DriverMeetingCode.filter(id=code_record.id).update(
            is_used=True,
            verified_by=request.user,
            verified_at=datetime.now()
        )
        
        # Получаем информацию о водителе
        driver = await UsersUser.filter(id=code_record.id_driver).first()
        driver_data = {
            "id": driver.id,
            "name": driver.name,
            "surname": driver.surname,
            "phone": driver.phone
        }
        
        # Получаем фото водителя
        driver_photo = await UsersUserPhoto.filter(id_user=driver.id).first()
        if driver_photo and driver_photo.photo_path:
            driver_data["photo_path"] = driver_photo.photo_path
        else:
            driver_data["photo_path"] = not_user_photo
        
        # Получаем информацию о машине водителя
        driver_car = await UsersCar.filter(id_driver=driver.id, isActive=True).first()
        if driver_car:
            driver_data["car"] = {
                "mark": driver_car.mark,
                "model": driver_car.model,
                "color": driver_car.color,
                "state_number": driver_car.state_number
            }
        
        logger.info(
            f"Parent {request.user} verified driver {code_record.id_driver}",
            extra={
                "parent_id": request.user,
                "driver_id": code_record.id_driver,
                "road_id": item.id_schedule_road,
                "code_id": code_record.id,
                "event_type": "parent_driver_verified"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Водитель успешно верифицирован! Можете передавать ребенка.",
            "driver": driver_data,
            "verified_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(
            f"Error verifying driver by parent: {str(e)}",
            extra={
                "parent_id": request.user,
                "road_id": item.id_schedule_road,
                "error": str(e),
                "event_type": "parent_driver_verification_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при верификации водителя"
        }, 500)


# ============================================================================
# BE-MVP-009: Автоматическое еженедельное списание
# ============================================================================

@router.get("/payment_schedule/{schedule_id}")
async def get_payment_schedule(request: Request, schedule_id: int):
    """
    BE-MVP-009: Получение информации о расписании платежей для контракта.
    
    Args:
        request: Объект запроса с user ID
        schedule_id: ID контракта
        
    Returns:
        JSONResponse: Информация о расписании платежей
    """
    try:
        # Проверяем, что контракт принадлежит пользователю
        contract = await DataSchedule.filter(id=schedule_id, id_user=request.user).first()
        if not contract:
            return JSONResponse({
                "status": False,
                "message": "Контракт не найден"
            }, 404)
        
        # Получаем расписание платежей
        payment_schedule = await WeeklyPaymentSchedule.filter(
            id_schedule=schedule_id,
            isActive=True
        ).first()
        
        if not payment_schedule:
            return JSONResponse({
                "status": True,
                "message": "Расписание платежей не настроено",
                "has_schedule": False
            })
        
        # Получаем историю последних платежей
        payment_history = await WeeklyPaymentHistory.filter(
            id_schedule=schedule_id
        ).order_by("-datetime_create").limit(10).values(
            "id", "amount", "status", "error_message", "datetime_create"
        )
        
        # Форматируем даты
        for payment in payment_history:
            if payment["datetime_create"]:
                payment["datetime_create"] = payment["datetime_create"].isoformat()
        
        return JSONResponse({
            "status": True,
            "message": "Success",
            "has_schedule": True,
            "schedule": {
                "id": payment_schedule.id,
                "amount": float(payment_schedule.amount),
                "next_payment_date": str(payment_schedule.next_payment_date),
                "last_payment_date": str(payment_schedule.last_payment_date) if payment_schedule.last_payment_date else None,
                "status": payment_schedule.status,
                "failed_attempts": payment_schedule.failed_attempts,
                "last_error": payment_schedule.last_error
            },
            "payment_history": payment_history
        })
        
    except Exception as e:
        logger.error(
            f"Error getting payment schedule: {str(e)}",
            extra={
                "user_id": request.user,
                "schedule_id": schedule_id,
                "error": str(e),
                "event_type": "payment_schedule_get_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при получении расписания платежей"
        }, 500)


@router.post("/payment_schedule/resume/{schedule_id}")
async def resume_payment_schedule(request: Request, schedule_id: int):
    """
    BE-MVP-009: Возобновление приостановленного расписания платежей.
    
    Родитель может возобновить контракт после пополнения баланса.
    
    Args:
        request: Объект запроса с user ID
        schedule_id: ID контракта
        
    Returns:
        JSONResponse: Результат возобновления
    """
    try:
        from datetime import date, timedelta
        
        # Проверяем, что контракт принадлежит пользователю
        contract = await DataSchedule.filter(id=schedule_id, id_user=request.user).first()
        if not contract:
            return JSONResponse({
                "status": False,
                "message": "Контракт не найден"
            }, 404)
        
        # Получаем расписание платежей
        payment_schedule = await WeeklyPaymentSchedule.filter(
            id_schedule=schedule_id,
            isActive=True
        ).first()
        
        if not payment_schedule:
            return JSONResponse({
                "status": False,
                "message": "Расписание платежей не найдено"
            }, 404)
        
        if payment_schedule.status != 'suspended':
            return JSONResponse({
                "status": False,
                "message": "Расписание не приостановлено"
            }, 400)
        
        # Проверяем баланс или наличие карты
        card = await DataDebitCard.filter(
            id_user=request.user,
            isActive=True
        ).first()
        
        if not card:
            return JSONResponse({
                "status": False,
                "message": "Добавьте карту для возобновления платежей"
            }, 400)
        
        # Возобновляем расписание
        next_date = date.today() + timedelta(days=7)
        await WeeklyPaymentSchedule.filter(id=payment_schedule.id).update(
            status='active',
            failed_attempts=0,
            last_error=None,
            next_payment_date=next_date,
            id_card=card.id,
            datetime_update=datetime.now()
        )
        
        # Активируем контракт
        await DataSchedule.filter(id=schedule_id).update(
            isActive=True
        )
        
        logger.info(
            f"Payment schedule resumed for contract {schedule_id}",
            extra={
                "user_id": request.user,
                "schedule_id": schedule_id,
                "next_payment_date": str(next_date),
                "event_type": "payment_schedule_resumed"
            }
        )
        
        # Уведомляем пользователя
        await sendPush(
            user_id=request.user,
            title="Контракт возобновлен",
            body=f"Контракт успешно возобновлен. Следующее списание: {next_date}",
            data={"type": "contract_resumed", "schedule_id": schedule_id}
        )
        
        return JSONResponse({
            "status": True,
            "message": "Расписание платежей успешно возобновлено",
            "next_payment_date": str(next_date)
        })
        
    except Exception as e:
        logger.error(
            f"Error resuming payment schedule: {str(e)}",
            extra={
                "user_id": request.user,
                "schedule_id": schedule_id,
                "error": str(e),
                "event_type": "payment_schedule_resume_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при возобновлении расписания"
        }, 500)


# ============================================================================
# BE-MVP-013: API контактов назначенного водителя
# ============================================================================

@router.get("/driver_contact/{schedule_id}")
async def get_driver_contact(request: Request, schedule_id: int):
    """
    BE-MVP-013: Получение контактов водителя для активного контракта.
    
    Родитель может получить ФИО, телефон, фото и информацию о машине
    водителя, назначенного на его контракт.
    
    Args:
        request: Объект запроса с user ID
        schedule_id: ID контракта/расписания
        
    Returns:
        JSONResponse: Контакты водителя и информация о машине
    """
    try:
        # Проверяем, что контракт принадлежит пользователю
        schedule = await DataSchedule.filter(
            id=schedule_id,
            id_user=request.user,
            isActive=True
        ).first()
        
        if not schedule:
            logger.warning(
                f"User {request.user} attempted to access non-existent or inactive schedule {schedule_id}",
                extra={
                    "user_id": request.user,
                    "schedule_id": schedule_id,
                    "event_type": "driver_contact_schedule_not_found"
                }
            )
            return JSONResponse({
                "status": False,
                "message": "Контракт не найден или неактивен"
            }, 404)
        
        # Получаем маршруты контракта
        roads = await DataScheduleRoad.filter(
            id_schedule=schedule_id,
            isActive=True
        ).values_list("id", flat=True)
        
        if not roads:
            return JSONResponse({
                "status": False,
                "message": "Маршруты не найдены"
            }, 404)
        
        # Получаем назначенного водителя (берем первый маршрут)
        driver_assignment = await DataScheduleRoadDriver.filter(
            id_schedule_road__in=roads,
            isActive=True
        ).first()
        
        if not driver_assignment:
            logger.info(
                f"No driver assigned to schedule {schedule_id}",
                extra={
                    "user_id": request.user,
                    "schedule_id": schedule_id,
                    "event_type": "driver_contact_no_driver"
                }
            )
            return JSONResponse({
                "status": False,
                "message": "Водитель еще не назначен на этот контракт"
            }, 404)
        
        driver_id = driver_assignment.id_driver
        
        # Получаем информацию о водителе
        driver = await UsersUser.filter(id=driver_id).first()
        if not driver:
            return JSONResponse({
                "status": False,
                "message": "Водитель не найден"
            }, 404)
        
        # Получаем фото водителя
        driver_photo = await UsersUserPhoto.filter(
            id_user=driver_id,
            isActive=True
        ).first()
        
        photo_url = None
        if driver_photo and driver_photo.photo:
            photo_url = driver_photo.photo
        
        # Получаем информацию о машине водителя
        driver_car = await UsersCar.filter(
            id_user=driver_id,
            isActive=True
        ).first()
        
        car_info = None
        if driver_car:
            # Получаем марку машины
            car_mark = await DataCarMark.filter(id=driver_car.id_mark).first()
            # Получаем модель машины
            car_model = await DataCarModel.filter(id=driver_car.id_model).first()
            # Получаем цвет
            car_color = await DataColor.filter(id=driver_car.id_color).first()
            
            car_info = {
                "mark": car_mark.title if car_mark else None,
                "model": car_model.title if car_model else None,
                "color": car_color.title if car_color else None,
                "number": driver_car.number if driver_car.number else None,
                "year": driver_car.year if driver_car.year else None
            }
        
        # Логируем успешный просмотр контактов
        logger.info(
            f"User {request.user} viewed driver {driver_id} contact for schedule {schedule_id}",
            extra={
                "user_id": request.user,
                "driver_id": driver_id,
                "schedule_id": schedule_id,
                "event_type": "driver_contact_viewed"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Success",
            "driver": {
                "id": driver.id,
                "name": driver.name,
                "surname": driver.surname,
                "patronymic": driver.patronymic if driver.patronymic else None,
                "phone": driver.phone,
                "photo": photo_url,
                "car": car_info
            }
        })
        
    except Exception as e:
        logger.error(
            f"Error getting driver contact: {str(e)}",
            extra={
                "user_id": request.user,
                "schedule_id": schedule_id,
                "error": str(e),
                "event_type": "driver_contact_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при получении контактов водителя"
        }, 500)


# ============================================================================
# BE-MVP-014: Прямая связь родитель-водитель
# ============================================================================

@router.post("/create_driver_chat/{schedule_id}")
async def create_driver_chat(request: Request, schedule_id: int):
    """
    BE-MVP-014: Создание чата между родителем и водителем для активного контракта.
    
    Родитель может создать прямой чат с водителем, назначенным на его контракт,
    для быстрой коммуникации.
    
    Args:
        request: Объект запроса с user ID
        schedule_id: ID контракта/расписания
        
    Returns:
        JSONResponse: ID созданного чата или существующего
    """
    try:
        # Проверяем, что контракт принадлежит пользователю
        schedule = await DataSchedule.filter(
            id=schedule_id,
            id_user=request.user,
            isActive=True
        ).first()
        
        if not schedule:
            logger.warning(
                f"User {request.user} attempted to create chat for non-existent schedule {schedule_id}",
                extra={
                    "user_id": request.user,
                    "schedule_id": schedule_id,
                    "event_type": "driver_chat_schedule_not_found"
                }
            )
            return JSONResponse({
                "status": False,
                "message": "Контракт не найден или неактивен"
            }, 404)
        
        # Получаем маршруты контракта
        roads = await DataScheduleRoad.filter(
            id_schedule=schedule_id,
            isActive=True
        ).values_list("id", flat=True)
        
        if not roads:
            return JSONResponse({
                "status": False,
                "message": "Маршруты не найдены"
            }, 404)
        
        # Получаем назначенного водителя
        driver_assignment = await DataScheduleRoadDriver.filter(
            id_schedule_road__in=roads,
            isActive=True
        ).first()
        
        if not driver_assignment:
            logger.info(
                f"No driver assigned to schedule {schedule_id}",
                extra={
                    "user_id": request.user,
                    "schedule_id": schedule_id,
                    "event_type": "driver_chat_no_driver"
                }
            )
            return JSONResponse({
                "status": False,
                "message": "Водитель еще не назначен на этот контракт"
            }, 404)
        
        driver_id = driver_assignment.id_driver
        
        # Проверяем, существует ли уже чат между этими пользователями
        # Ищем чаты, где оба пользователя являются участниками
        parent_chats = await ChatsChatParticipant.filter(
            id_user=request.user
        ).values_list("id_chat", flat=True)
        
        driver_chats = await ChatsChatParticipant.filter(
            id_user=driver_id
        ).values_list("id_chat", flat=True)
        
        # Находим общие чаты
        common_chats = set(parent_chats) & set(driver_chats)
        
        if common_chats:
            # Берем первый общий чат
            existing_chat_id = list(common_chats)[0]
            
            logger.info(
                f"Returning existing chat {existing_chat_id} between parent {request.user} and driver {driver_id}",
                extra={
                    "parent_id": request.user,
                    "driver_id": driver_id,
                    "schedule_id": schedule_id,
                    "chat_id": existing_chat_id,
                    "event_type": "driver_chat_existing_returned"
                }
            )
            
            return JSONResponse({
                "status": True,
                "message": "Чат уже существует",
                "chat_id": existing_chat_id,
                "is_new": False
            })
        
        # Создаем новый чат
        from datetime import datetime
        chat = await ChatsChat.create(
            isActive=True,
            datetime_create=datetime.now()
        )
        
        # Добавляем родителя как участника
        await ChatsChatParticipant.create(
            id_chat=chat.id,
            id_user=request.user
        )
        
        # Добавляем водителя как участника
        await ChatsChatParticipant.create(
            id_chat=chat.id,
            id_user=driver_id
        )
        
        # Логируем создание чата
        logger.info(
            f"Created chat {chat.id} between parent {request.user} and driver {driver_id} for schedule {schedule_id}",
            extra={
                "parent_id": request.user,
                "driver_id": driver_id,
                "schedule_id": schedule_id,
                "chat_id": chat.id,
                "event_type": "driver_chat_created"
            }
        )
        
        # Отправляем уведомление водителю о новом чате
        try:
            parent = await UsersUser.filter(id=request.user).first()
            parent_name = f"{parent.name} {parent.surname}" if parent else "Родитель"
            
            await sendPush(
                user_id=driver_id,
                title="Новый чат",
                body=f"{parent_name} начал чат с вами",
                data={
                    "type": "new_chat",
                    "chat_id": chat.id,
                    "parent_id": request.user,
                    "schedule_id": schedule_id
                }
            )
        except Exception as e:
            logger.error(
                f"Failed to send new chat notification: {str(e)}",
                extra={
                    "chat_id": chat.id,
                    "driver_id": driver_id,
                    "error": str(e),
                    "event_type": "driver_chat_notification_failed"
                }
            )
        
        return JSONResponse({
            "status": True,
            "message": "Чат успешно создан",
            "chat_id": chat.id,
            "is_new": True,
            "driver_id": driver_id
        })
        
    except Exception as e:
        logger.error(
            f"Error creating driver chat: {str(e)}",
            extra={
                "user_id": request.user,
                "schedule_id": schedule_id,
                "error": str(e),
                "event_type": "driver_chat_create_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при создании чата"
        }, 500)


# ============================================================================
# BE-MVP-028: API истории транзакций
# ============================================================================

@router.get("/transactions")
async def get_transaction_history(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    start_date: str = None,
    end_date: str = None,
    transaction_type: str = None
):
    """
    BE-MVP-028: Получение истории транзакций пользователя.
    
    Пользователь может просмотреть свою историю платежей с фильтрацией и пагинацией.
    
    Args:
        request: Объект запроса
        page: Номер страницы (по умолчанию 1)
        per_page: Количество на странице (по умолчанию 20)
        start_date: Начальная дата (формат: YYYY-MM-DD)
        end_date: Конечная дата (формат: YYYY-MM-DD)
        transaction_type: Тип транзакции (deposit/withdrawal/payment)
        
    Returns:
        JSONResponse: История транзакций с пагинацией
    """
    try:
        # Строим запрос с фильтрами
        query = HistoryPaymentTink.filter(id_user=request.user)
        
        # Фильтр по датам
        if start_date:
            from datetime import datetime
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(datetime_create__gte=start_dt)
        
        if end_date:
            from datetime import datetime
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(datetime_create__lte=end_dt)
        
        # Фильтр по типу транзакции
        if transaction_type:
            if transaction_type == "deposit":
                query = query.filter(amount__gt=0)
            elif transaction_type == "withdrawal":
                query = query.filter(amount__lt=0)
        
        # Подсчет общего количества
        total = await query.count()
        
        # Пагинация
        offset = (page - 1) * per_page
        transactions = await query.order_by("-datetime_create").offset(offset).limit(per_page).all()
        
        # Формируем результат
        result = []
        for transaction in transactions:
            result.append({
                "id": transaction.id,
                "amount": float(transaction.amount),
                "datetime_create": transaction.datetime_create.isoformat() if transaction.datetime_create else None,
                "status": transaction.status if hasattr(transaction, 'status') else "completed",
                "description": transaction.description if hasattr(transaction, 'description') else None,
                "payment_id": transaction.payment_id if hasattr(transaction, 'payment_id') else None
            })
        
        # Подсчет общей суммы
        total_amount = sum(float(t.amount) for t in transactions)
        
        logger.info(
            f"User {request.user} viewed transaction history",
            extra={
                "user_id": request.user,
                "page": page,
                "per_page": per_page,
                "total": total,
                "filters": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "transaction_type": transaction_type
                },
                "event_type": "user_transactions_viewed"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Success",
            "transactions": result,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            },
            "summary": {
                "total_amount": total_amount,
                "count": len(result)
            }
        })
        
    except Exception as e:
        logger.error(
            f"Error getting transaction history: {str(e)}",
            extra={
                "user_id": request.user,
                "error": str(e),
                "event_type": "user_transactions_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при получении истории транзакций"
        }, 500)
