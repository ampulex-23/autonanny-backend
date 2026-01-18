import datetime
import traceback
import logging

from const.orders_const import get_schedules_responses, schedule_not_found, \
    get_today_schedule, WantSchedule, \
    get_driver_schedules, DeclineRoads
from defs import get_date_from_datetime, sendPush, get_time_drive

logger = logging.getLogger(__name__)
from models.authentication_db import UsersBearerToken
from models.orders_db import DataSchedule, DataScheduleOtherParametrs, DataScheduleRoad, \
    DataScheduleRoadAddress, \
    DataScheduleRoadDriver, WaitDataScheduleRoadDriver, DataOrder, DataScheduleRoadChild, \
    DataDrivingStatus
from models.users_db import UsersUser, UsersUserPhoto, UsersReferalUser, DataDebitCard, DataUserBalance, \
    HistoryNotification, UsersChild, ChildMedicalInfo, ChildEmergencyContact, DriverMeetingCode
from models.users_db import DataUserBalanceHistory, HistoryRequestPayment
from const.users_const import debit_card_not_found, insufficient_balance, success_answer
from const.static_data_const import not_user_photo, access_forbidden, DictToModel
from models.drivers_db import UsersDriverData, UsersCar, DataDriverMode
from models.static_data_db import DataColor, DataCarModel, DataCarMark
from fastapi import APIRouter, Request, Depends
from const.dependency import has_access_driver
from const.drivers_const import *
import decimal
import json
import uuid
from utils.response_helpers import generate_responses

router = APIRouter()

#TODO: сделать проверку доступа только админам, родителям заказа, отклика
@router.post("/get_driver",
             responses=generate_responses([access_forbidden,
                                           driver_not_found,
                                           get_driver]))
async def get_driver_by_id(request: Request, item: GetDriver):
    if request.user != item.id and await UsersDriverData.filter(id_driver=item.id).count()>0:
        return access_forbidden
    if await UsersUser.filter(id=item.id).count() == 0 or await UsersDriverData.filter(id_driver=item.id).count() == 0:
        return driver_not_found

    data = DictToModel(await UsersUser.filter(id=item.id).first().values())
    driver_data = DictToModel(await UsersDriverData.filter(id_driver=item.id).first().values())
    photo = await UsersUserPhoto.filter(id_user=item.id).first().values("photo_path")
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
                         "driver": {
                             "surname": data.surname,
                             "name": data.name,
                             "inn": None if hasattr(driver_data, "inn") is True else driver_data.inn,
                             "photo_path": photo,
                             "video_path": driver_data.video_url,
                             "date_reg": data.datetime_create.isoformat(),
                             "carData": car
                         }})

@router.post("/get-my-referals",
             responses=generate_responses([get_my_referals]))
async def get_driver_referals(request: Request, item: GetDriverReferals):
    count = await UsersReferalUser.filter(id_user=request.user).count()
    data = await UsersReferalUser.filter(id_user=request.user).order_by("-id").offset(item.offset).limit(item.limit).values()
    for driver in data:
        photo = await UsersUserPhoto.filter(id_user=driver["id_user_referal"]).first().values("photo_path")
        photo = photo["photo_path"] if photo is not None and "photo_path" in photo else not_user_photo
        driver["photo_path"] = photo
        driver["name"] = (await UsersUser.filter(id=driver["id"]).first().values())["name"]
        driver["status"] = False
        driver["id"] = driver["id_user_referal"]
        del driver["id_user"]
        del driver["id_user_referal"]
    return JSONResponse({"status": True,
                         "message": "Success!",
                         "total": count,
                         "referals": data})

@router.post("/start-driver-mode",
             dependencies=[Depends(has_access_driver)],
             responses=generate_responses([start_current_drive_mode]))
async def start_driver_mode(request: Request, item: NowLocation):
    await DataDriverMode.filter(id_driver=request.user).delete()
    data = await DataDriverMode.create(id_driver=request.user, latitude=item.latitude, longitude=item.longitude,
                                       websocket_token=str(uuid.uuid4())+str(uuid.uuid4())+str(uuid.uuid4()), isActive=True)
    return JSONResponse({"status": True,
                         "message": "Success!",
                         "driver-token": data.websocket_token})

@router.get("/get_current_order",
            dependencies=[Depends(has_access_driver)],
            responses=generate_responses([get_current_order]))
async def get_current_order(request: Request):
    data = await DataOrder.filter(id_driver=request.user, isActive=True).all().values("id")
    orders = []
    for order in data:
        orders.append(order["id"])
    return JSONResponse({"status": True,
                         "message": "Success!",
                         "orders": orders})

@router.post("/request-payment",
             dependencies=[Depends(has_access_driver)],
             responses=generate_responses([debit_card_not_found,
                                           insufficient_balance,
                                           success_answer]))
async def send_payment_requests(request: Request, item: SendPaymentRequest):
    if await DataDebitCard.filter(id_user=request.user, id=item.id_card).count() == 0:
        return debit_card_not_found
    if await DataUserBalance.filter(id_user=request.user).count() == 0 or \
            await DataUserBalance.filter(id_user=request.user, money__lte=50).count() > 0:
        return insufficient_balance
    if item.type_request == 1:
        money = await DataUserBalance.filter(id_user=request.user).order_by("-id").first().values()
        if (item.amount is not None and decimal.Decimal(item.amount) > money["money"]) or item.amount <= 0:
            return insufficient_balance
        else:
            item.amount = money["money"]
        await DataUserBalance.filter(id_user=request.user).update(money=money["money"]-decimal.Decimal(item.amount))
        history = await DataUserBalanceHistory.create(id_user=request.user, money=decimal.Decimal(-item.amount),
                                                    isComplete=True, description="Заявка на получение ЗП", id_task=-100)
        await HistoryRequestPayment.filter(id_user=request.user, id_card=item.id_card, id_history=history.id,
                                    money=decimal.Decimal(item.amount), isCashback=False, isSuccess=False, isActive=True)
        return success_answer
    else:
        return success_answer

@router.get("/get_schedules_requests",
            responses=generate_responses([get_schedules_responses,
                                          schedule_not_found,
                                          access_forbidden]))
async def get_schedule(request: Request, limit: Union[int, None] = 30, offset: Union[int, None] = 0):
    """
    Эндпоинт для получения всех расписаний

    Args:
        request (Request): Объект запроса
        limit (Union[int, None], optional): Количество расписаний. По умолчанию 30.
        offset (Union[int, None], optional): Смещение. По умолчанию к 0.

    Returns:
        JSONResponse: Ответ с расписаниями
    """
    schedules = await DataSchedule.all().limit(limit).offset(offset).values \
        ("id", "id_user", "title", "description", "children_count",
         "id_tariff", "week_days", "duration")
    valid_schedules = []
    for schedule in schedules:
        stop = False  # Флаг - если он True, значит с маршрутами в расписании что-то не так => расписание не выводится
        photo = await UsersUserPhoto.filter(id_user=schedule["id"]).first().values()
        schedule["user"] = {
            "id_user": schedule["id_user"],
            "name": (await UsersUser.filter(id=schedule["id_user"]).first().values())["name"],
            "photo_path": not_user_photo if photo is None or len(photo) == 0 else photo["photo_path"]
        }
        schedule["week_days"] = [int(x) for x in schedule["week_days"].split(";") if x.isdigit()]
        other_parametrs = await DataScheduleOtherParametrs.filter(id_schedule=schedule["id"],
                                                                  isActive=True).order_by("id").all().values()
        other_parametrs_data = []
        for parametr in other_parametrs:
            other_parametrs_data.append({
                "parametr": parametr["id_other_parametr"],
                "count": parametr["amount"]
            })
        schedule["other_parametrs"] = other_parametrs_data
        roads = await DataScheduleRoad.filter(id_schedule=schedule["id"], isActive=True).order_by("id").all().values()

        all_price = 0
        available_roads = []
        for road in roads:
            try:
                road["type_drive"] = [int(x) for x in road["type_drive"].split(";") if x.isdigit()]
                addresses = await DataScheduleRoadAddress.filter(id_schedule_road=road["id"]).order_by("id").all().values()
                data_addresses = []
                price_road = road.get("amount", -1)
                if await DataScheduleRoadDriver.filter(id_schedule_road=road["id"], isActive=True).count() > 0:  # Если у маршрута уже есть исполнитель
                    continue

                for address in addresses:
                    address_data = {
                        "from_address": {
                            "address": address["from_address"],
                            "location": {
                                "longitude": address["from_lon"],
                                "latitude": address["from_lat"]
                            }
                        },
                        "to_address": {
                            "address": address["to_address"],
                            "location": {
                                "longitude": address["to_lon"],
                                "latitude": address["to_lat"]
                            }
                        }
                    }
                    data_addresses.append(address_data)

                road["addresses"] = data_addresses
                road["salary"] = round(float(price_road), 2)
                all_price += price_road

                road.pop("id_schedule", None)
                road.pop("amount", None)
                road.pop("isActive", None)
                road.pop("datetime_create", None)
                available_roads.append(road)
            except Exception as e:
                stop = True
                break
        if stop:  # Если в расписании что-то не так => расписание не выводится
            continue
        if roads is None or len(available_roads) == 0:  # Если в расписании нет маршрутов => расписание не выводится
            continue
        schedule["roads"] = available_roads
        schedule["all_salary"] = round(float(all_price), 2)  # Ensure total salary is float
        del schedule["id_user"]
        valid_schedules.append(schedule)

    return JSONResponse({"status": True,
                         "message": "Success!",
                         "schedules": valid_schedules}, 200)

@router.get("/get_full_roads_info")
async def get_full_roads_info(request: Request,
                              road_ids: str):  # road_ids как строка вида "1,2,3"
    """
    Эндпоинт для получения информации о конкретных дорогах и их расписаниях

    Example:

        Пример выходных данных:

        {
          "status": true,
          "message": "Success!",
          "schedules": [
            {
              "id": 19,
              "title": "тест",
              "description": "",
              "children_count": 4,
              "id_tariff": 3,
              "week_days": [
                1
              ],
              "duration": 7,
              "user": {
                "id_user": 21,
                "name": "Максим",
                "photo_path": "https://nyanyago.ru/api/v1.0/files/not_user_photo.png"
              },
              "other_parametrs": [],
              "roads": [
                {
                  "id": 43,
                  "type_drive": [
                    0
                  ],
                  "start_time": "19:15",
                  "end_time": "22:15",
                  "week_day": 5,
                  "title": "нг",
                  "addresses": [
                    {
                      "from_address": {
                        "address": "Россия",
                        "location": {
                          "longitude": 105.31875610351562,
                          "latitude": 61.524009704589844
                        }
                      },
                      "to_address": {
                        "address": "Россия",
                        "location": {
                          "longitude": 105.31875610351562,
                          "latitude": 61.524009704589844
                        }
                      }
                    }
                  ],
                  "salary": 355.35
                },
                {
                  "id": 45,
                  "type_drive": [
                    0
                  ],
                  "start_time": "05:00",
                  "end_time": "10:00",
                  "week_day": 1,
                  "title": "в лес",
                  "addresses": [
                    {
                      "from_address": {
                        "address": "Лесной, Свердловская обл., Россия",
                        "location": {
                          "longitude": 59.790401458740234,
                          "latitude": 58.63566589355469
                        }
                      },
                      "to_address": {
                        "address": "Плёс, Ивановская обл., Россия",
                        "location": {
                          "longitude": 41.512271881103516,
                          "latitude": 57.46049499511719
                        }
                      }
                    }
                  ],
                  "salary": 150
                }
              ],
              "all_salary": 505.35
            }
          ]
        }

    Args:
        request (Request): Объект запроса
        road_ids (str): Строка с ID дорог, разделенных запятыми (например, "1,2,3")

    Returns:
        JSONResponse: Ответ с информацией о дорогах и их расписаниях
    """
    try:
        # Преобразуем строку road_ids в список целых чисел
        road_id_list = [int(x) for x in road_ids.split(",") if x.isdigit()]
        if not road_id_list:
            return JSONResponse(
                {"status": False, "message": "No valid road IDs provided"}, 400)

        # Получаем все дороги по указанным ID (без фильтра isActive)
        roads = await DataScheduleRoad.filter(id__in=road_id_list).order_by(
            "id").all().values()
        if not roads:
            return JSONResponse({"status": False, "message": "No roads found"}, 404)

        valid_schedules = {}
        # Группируем дороги по расписаниям
        for road in roads:
            schedule_id = road["id_schedule"]
            if schedule_id not in valid_schedules:
                # Получаем данные расписания
                schedule = await DataSchedule.filter(id=schedule_id).first().values(
                    "id", "id_user", "title", "description", "children_count",
                    "id_tariff", "week_days", "duration"
                )
                if not schedule:
                    schedule = {
                        "id": schedule_id,
                        "title": "Unknown schedule",
                        "description": "No description",
                        "children_count": 0,
                        "id_tariff": None,
                        "week_days": "1",
                        "duration": 0
                    }

                # Добавляем информацию о пользователе
                photo = await UsersUserPhoto.filter(
                    id_user=schedule["id"]).first().values()
                user_data = await UsersUser.filter(
                    id=schedule["id_user"]).first().values() if schedule.get(
                    "id_user") else None
                schedule["user"] = {
                    "id_user": schedule.get("id_user", 0),
                    "name": user_data["name"] if user_data else "Unknown user",
                    "photo_path": not_user_photo if photo is None or len(
                        photo) == 0 else photo.get("photo_path", not_user_photo)
                }
                schedule["week_days"] = [int(x) for x in
                                         schedule["week_days"].split(";") if
                                         x.isdigit()] if schedule["week_days"] else [1]

                # Получаем дополнительные параметры
                other_parametrs = await DataScheduleOtherParametrs.filter(
                    id_schedule=schedule_id, isActive=True
                ).order_by("id").all().values()
                schedule["other_parametrs"] = [{
                    "parametr": parametr["id_other_parametr"] if parametr.get(
                        "id_other_parametr") else 0,
                    "count": parametr["amount"] if parametr.get(
                        "amount") is not None else 0
                } for parametr in other_parametrs] if other_parametrs else []

                schedule["roads"] = []
                valid_schedules[schedule_id] = schedule

            # Обрабатываем данные дороги (в случае ошибки - отправляем моковые данные) (TODO)
            road_data = dict()
            road_data["id"] = road["id"]
            road_data["type_drive"] = [int(x) for x in road["type_drive"].split(";") if
                                       x.isdigit()] if road.get("type_drive") else [0]
            road_data["start_time"] = road["start_time"] if road.get("start_time", 0) is not None else 0
            road_data["end_time"] = road["end_time"] if road.get("end_time", 0) is not None else 0
            road_data["week_day"] = road["week_day"] if road.get("week_day", -1) is not None else -1
            road_data["title"] = road["title"] if road.get("title") else "Unknown road"

            # Получаем адреса
            addresses = await DataScheduleRoadAddress.filter(
                id_schedule_road=road["id"]
            ).order_by("id").all().values()
            data_addresses = []
            for address in addresses:
                address_data = {
                    "from_address": {
                        "address": address["from_address"] if address.get(
                            "from_address") else "Unknown from address",
                        "location": {
                            "longitude": address["from_lon"] if address.get(
                                "from_lon") is not None else 0.0,
                            "latitude": address["from_lat"] if address.get(
                                "from_lat") is not None else 0.0
                        }
                    },
                    "to_address": {
                        "address": address["to_address"] if address.get(
                            "to_address") else "Unknown to address",
                        "location": {
                            "longitude": address["to_lon"] if address.get(
                                "to_lon") is not None else 0.0,
                            "latitude": address["to_lat"] if address.get(
                                "to_lat") is not None else 0.0
                        }
                    }
                }
                data_addresses.append(address_data)
            road_data["addresses"] = data_addresses if data_addresses else [{
                "from_address": {"address": "Unknown",
                                 "location": {"longitude": 0.0, "latitude": 0.0}},
                "to_address": {"address": "Unknown",
                               "location": {"longitude": 0.0, "latitude": 0.0}}
            }]

            price_road = road.get("amount")
            road_data["salary"] = round(float(price_road),
                                        2) if price_road is not None else 0.0
            valid_schedules[schedule_id]["roads"].append(road_data)

        # Финальная обработка и подсчет общей стоимости
        result_schedules = []
        for schedule in valid_schedules.values():
            all_price = sum(road["salary"] for road in schedule["roads"])
            schedule["all_salary"] = round(float(all_price), 2)
            del schedule["id_user"]
            result_schedules.append(schedule)

        return JSONResponse({
            "status": True,
            "message": "Success!",
            "schedules": result_schedules
        }, 200)

    except ValueError:
        return JSONResponse({"status": False, "message": "Invalid road_ids format"},
                            400)
    except Exception as e:
        return JSONResponse({"status": False, "message": f"Error: {str(e)}"}, 500)

@router.get("/get_my_schedules",
             responses=generate_responses([get_driver_schedules,
                                           schedule_not_found,
                                           access_forbidden]))
async def get_my_schedules(request: Request, limit: Union[int, None] = 30, offset: Union[int, None] = 0):
    # TODO: Это не должно работать... См. get_driver_roads
    data = await DataScheduleRoadDriver.filter(id_driver=request.user, isActive=True, isRepeat=True).all().values()
    schedules = await DataScheduleRoadDriver.filter(isActive=True).limit(limit).offset(offset).all().values\
                       ("id", "id_user", "title", "description", "children_count",
                                                        "id_tariff", "week_days", "duration")  # Нет таких данных в `DataScheduleRoadDriver`
    for schedule in schedules:
        photo = await UsersUserPhoto.filter(id_user=schedule["id"]).first().values()
        schedule["user"] = {
            "id_user": schedule["id_user"],
            "name": (await UsersUser.filter(id=schedule["id_user"]).first().values())["name"],
            "photo_path": not_user_photo if photo is None or len(photo) == 0 else photo["photo_path"]
        }
        schedule["week_days"] = [int(x) for x in schedule["week_days"].split(";")]
        other_parametrs = await DataScheduleOtherParametrs.filter(id_schedule=schedule["id"],
                                                                  isActive=True).order_by("id").all().values()
        other_parametrs_data = []
        for parametr in other_parametrs:
            other_parametrs_data.append({
                "parametr": parametr["id_other_parametr"],
                "count": parametr["amount"]
            })
        schedule["other_parametrs"] = other_parametrs_data
        roads = await DataScheduleRoad.filter(id_schedule=schedule["id"], isActive=True).order_by("id").all().values()
        for road in roads:
            road["type_drive"] = [int(x) for x in road["type_drive"].split(";")]
            addresses = await DataScheduleRoadAddress.filter(id_schedule_road=road["id"]).order_by("id").all().values()
            data_addresses = []
            for address in addresses:
                address_data = {
                                    "from_address": {
                                        "address": address["from_address"],
                                        "location": {
                                            "longitude": address["from_lon"],
                                            "latitude": address["from_lat"]
                                        }
                                    },
                                    "to_address": {
                                        "address": address["to_address"],
                                        "location": {
                                            "longitude": address["to_lon"],
                                            "latitude": address["to_lat"]
                                        }
                                    }
                }
                data_addresses.append(address_data)
            road["addresses"] = data_addresses
            road["salary"] = 0
            del road["id_schedule"]
            del road["isActive"]
            del road["datetime_create"]
        schedule["roads"] = roads
        del schedule["id_user"]
        schedule["all_salary"] = 0
    print(schedules)
    return JSONResponse({"status": True,
                         "message": "Success!",
                         "schedules": schedules}, 200)

@router.get("/get_driver_roads")
async def get_driver_roads(request: Request, limit: Union[int, None] = 30, offset: Union[int, None] = 0):
    data = await DataScheduleRoadDriver.filter(id_driver=request.user, isActive=True).limit(limit).offset(offset).all().values()
    return JSONResponse({"status": True,
                         "message": "Success!",
                         "roads_id": [x["id_schedule_road"] for x in data]}, 200)

@router.get("/get_today_schedule",
            responses=generate_responses([get_today_schedule]))
async def get_today_schedule(request: Request):
    all_road = await DataScheduleRoadDriver.filter(id_driver=request.user, isActive=True).all().values()
    result, today = [], int(datetime.datetime.now().date().weekday())
    for each in all_road:
        road = await DataScheduleRoad.filter(id=each["id_schedule_road"]).first().values()
        if int(road["week_day"]) != today:
            continue
        parent = await UsersUser.filter(id=(await DataSchedule.filter(
                                                id=road["id_schedule"]).first().values())["id_user"]).first().values()
        response = {
            "id": road["id"],
            "title": road["title"],
            "parent_name": parent["name"],
            "id_parent": parent["id"],
            "time": road["start_time"] + " - " + road["end_time"],
            "date": await get_date_from_datetime(datetime.datetime.now().date())
        }
        result.append(response)

    return JSONResponse({"status": True,
                         "message": "Success!",
                         "schedule": result})

@router.post(
    "/want_schedule_requests",
    responses=generate_responses([success_answer, schedule_not_found]),
)
async def want_schedule_requests(request: Request, item: WantSchedule):
    """
    Эндпоинт для отправки заявки на принятие маршрутов в расписании/контракте.
    В дальнейшем - клиент должен подтвердить (или отклонить) эту заявку с помощью
    `/orders/answer_schedule_responses`.
    
    ВАЖНО (BE-MVP-015): Водитель должен принимать ВСЕ маршруты программы.
    Частичное участие запрещено.

    Пример запроса:
        {
            "id_schedule": 1,
            "id_road": [1, 2, 3]
        }

    Args:
        request (Request): Объект запроса.
        item (WantSchedule): Объект с данными для отправки заявки.

    Returns:
        JSONResponse: Ответ в формате JSON.
    """
    if await DataSchedule.filter(id=item.id_schedule).count() != 1:
        return schedule_not_found
    schedule, req = (
        await DataSchedule.filter(id=item.id_schedule).first().values(),
        {},
    )
    
    # BE-MVP-015: Валидация полной программы - водитель должен принять ВСЕ маршруты
    all_schedule_roads = await DataScheduleRoad.filter(
        id_schedule=item.id_schedule,
        isActive=True
    ).all().values("id")
    all_road_ids = {road["id"] for road in all_schedule_roads}
    requested_road_ids = set(item.id_road)
    
    if requested_road_ids != all_road_ids:
        missing_roads = all_road_ids - requested_road_ids
        extra_roads = requested_road_ids - all_road_ids
        
        logger.warning(
            f"Driver {request.user} attempted partial schedule acceptance",
            extra={
                "driver_id": request.user,
                "schedule_id": item.id_schedule,
                "total_roads": len(all_road_ids),
                "requested_roads": len(requested_road_ids),
                "missing_roads": list(missing_roads),
                "extra_roads": list(extra_roads),
                "event_type": "partial_schedule_rejected"
            }
        )
        
        return JSONResponse(
            {
                "status": False,
                "message": "Водитель должен принять все маршруты программы. Частичное участие запрещено.",
                "details": {
                    "total_roads_count": len(all_road_ids),
                    "requested_roads_count": len(requested_road_ids),
                    "all_road_ids": list(all_road_ids)
                }
            },
            400,
        )
    
    # BE-MVP-012: Валидация максимального количества детей
    from const.orders_const import MAX_CHILDREN_PER_SCHEDULE
    total_children = 0
    for road_id in item.id_road:
        children_count = await DataScheduleRoadChild.filter(
            id_schedule_road=road_id,
            isActive=True
        ).count()
        total_children += children_count
    
    if total_children > MAX_CHILDREN_PER_SCHEDULE:
        logger.warning(
            f"Driver {request.user} attempted to accept schedule with {total_children} children (max: {MAX_CHILDREN_PER_SCHEDULE})",
            extra={
                "driver_id": request.user,
                "schedule_id": item.id_schedule,
                "children_count": total_children,
                "max_allowed": MAX_CHILDREN_PER_SCHEDULE,
                "event_type": "driver_too_many_children"
            }
        )
        return JSONResponse(
            {
                "status": False,
                "message": f"Максимальное количество детей на маршруте - {MAX_CHILDREN_PER_SCHEDULE}. В этом расписании {total_children} детей."
            },
            400,
        )
    
    for each in item.id_road:
        if (
            await DataScheduleRoad.filter(id_schedule=item.id_schedule, id=each).count()
            != 1
        ):
            return JSONResponse(
                {
                    "status": False,
                    "message": "Some of the roads do not belong to this schedule!",
                },
                404,
            )
        if (
            await DataScheduleRoadDriver.filter(
                id_schedule_road=each,
                isActive=True
            ).count()
            != 0
        ):
            return JSONResponse(
                {"status": False, "message": "Some of the roads already have drivers!"},
                404,
            )
        if await WaitDataScheduleRoadDriver.filter(id_road=each, id_driver=request.user, isActive=False).count() != 0:
            return JSONResponse(
                {"status": False, "message": "Some of the roads already accepted/declined"},
                404,
            )
    requests = []
    for each in item.id_road:
        req, _ = await WaitDataScheduleRoadDriver.get_or_create(
            id_driver=request.user, id_road=each, id_schedule=item.id_schedule, isActive=True
        )
        requests.append(
            {
                "id": req.id,
                "id_schedule": item.id_schedule,
                "id_road": each,
                "isActive": req.isActive,
            }
        )
    
    # BE-MVP-015: Логирование успешного принятия полной программы
    logger.info(
        f"Driver {request.user} accepted full schedule program",
        extra={
            "driver_id": request.user,
            "schedule_id": item.id_schedule,
            "roads_count": len(item.id_road),
            "road_ids": item.id_road,
            "event_type": "full_schedule_accepted"
        }
    )
    
    print(schedule["id_user"])
    fbid = (
        await UsersBearerToken.filter(id_user=schedule["id_user"])
        .order_by("-id")
        .first()
        .values()
    )
    print(fbid)
    try:
        await sendPush(
            fbid["fbid"],
            "Получена новая заявка",
            "По вашему контракту получен новый отклик от водителя",
            {"action": "order_request", "id_request": str([r["id"] for r in requests])},
        )
        await HistoryNotification.create(
            id_user=schedule["id_user"],
            title="Получена новая заявка",
            description="По вашему контракту получен новый отклик от водителя",
        )
    except Exception:
        print(traceback.format_exc())

    schedule = (
        await DataSchedule.filter(id=item.id_schedule).first().values()
    )
    schedule.pop("datetime_create", None)
    roads = []
    for each in item.id_road:
        road = await DataScheduleRoad.filter(id=each).first().values()
        road.pop("datetime_create", None)
        road["amount"] = round(float(road.get("amount", 0)), 2)
        roads.append(road)
    return JSONResponse(
        {
            "status": True,
            "message": "Success!",
            "schedule": schedule,
            "roads": roads,
            "requests": requests,
        },
        200,
    )

@router.post("/decline_roads_requests",)
async def decline_roads_requests(request: Request, item: DeclineRoads):
    """
    Эндпоинт для отказа водителем от маршрутов в расписании/контракте.

    Пример запроса:
        {
            "id_road": [1, 2, 3]
        }

    Args:
        request (Request): Объект запроса.
        item (WantSchedule): Объект с данными (id_road: List).

    Returns:
        JSONResponse: Ответ в формате JSON. Может быть сообщение об ошибке ("You do not have access to this road").
    """
    for each in item.id_road:
        if await DataScheduleRoadDriver.filter(id_schedule_road=each, id_driver=request.user).count() == 0:
            return JSONResponse({"status": False, "message": "You do not have access to this road"}, 404)
        await DataScheduleRoadDriver.filter(id_schedule_road=each, id_driver=request.user).update(isActive=False)

    return JSONResponse({"status": True, "message": "Success!"}, 200)


# ============================================================================
# BE-MVP-019: API просмотра информации о детях для водителя
# ============================================================================

@router.get("/children/{road_id}")
async def get_children_info(request: Request, road_id: int):
    """
    BE-MVP-019: Получение информации о детях для водителя.
    
    Водитель получает информацию о детях, которых он везет на конкретном маршруте.
    Включает: профиль ребенка, медицинскую информацию (аллергии!), экстренные контакты.
    
    Args:
        request: Объект запроса с driver ID
        road_id: ID маршрута (schedule_road)
        
    Returns:
        JSONResponse: Информация о детях на маршруте
    """
    try:
        # Проверяем, что водитель имеет доступ к этому маршруту
        driver_road = await DataScheduleRoadDriver.filter(
            id_schedule_road=road_id,
            id_driver=request.user,
            isActive=True
        ).first()
        
        if not driver_road:
            logger.warning(
                f"Driver {request.user} attempted to access road {road_id} without permission",
                extra={
                    "driver_id": request.user,
                    "road_id": road_id,
                    "event_type": "driver_unauthorized_child_access"
                }
            )
            return JSONResponse({
                "status": False,
                "message": "У вас нет доступа к этому маршруту"
            }, 403)
        
        # Получаем детей на этом маршруте
        road_children = await DataScheduleRoadChild.filter(
            id_schedule_road=road_id,
            isActive=True
        ).values_list("id_child", flat=True)
        
        if not road_children:
            return JSONResponse({
                "status": True,
                "message": "На этом маршруте нет детей",
                "children": [],
                "count": 0
            })
        
        # Получаем полную информацию о каждом ребенке
        children_data = []
        for child_id in road_children:
            # Базовая информация о ребенке
            child = await UsersChild.filter(id=child_id, isActive=True).first()
            if not child:
                continue
            
            child_info = {
                "id": child.id,
                "name": child.name,
                "surname": child.surname,
                "patronymic": child.patronymic,
                "age": child.age,
                "birthday": str(child.birthday) if child.birthday else None,
                "gender": child.gender,
                "photo_path": child.photo_path if child.photo_path else not_user_photo,
                "school_class": child.school_class,
                "character_notes": child.character_notes,
                "child_phone": child.child_phone
            }
            
            # BE-MVP-017: Медицинская информация (КРИТИЧНО для водителя!)
            medical_info = await ChildMedicalInfo.filter(
                id_child=child_id,
                isActive=True
            ).first()
            
            if medical_info:
                child_info["medical_info"] = {
                    "allergies": medical_info.allergies,  # КРИТИЧНО!
                    "chronic_diseases": medical_info.chronic_diseases,
                    "medications": medical_info.medications,
                    "blood_type": medical_info.blood_type,
                    "special_needs": medical_info.special_needs,
                    "has_medical_info": True
                }
                # Выделяем аллергии отдельно для быстрого доступа
                child_info["has_allergies"] = bool(medical_info.allergies)
                child_info["allergies_warning"] = medical_info.allergies if medical_info.allergies else None
            else:
                child_info["medical_info"] = None
                child_info["has_allergies"] = False
                child_info["allergies_warning"] = None
            
            # BE-MVP-018: Экстренные контакты (на случай ЧП)
            emergency_contacts = await ChildEmergencyContact.filter(
                id_child=child_id,
                isActive=True
            ).order_by("priority").values(
                "id", "name", "relationship", "phone", "priority"
            )
            
            child_info["emergency_contacts"] = emergency_contacts
            child_info["emergency_contacts_count"] = len(emergency_contacts)
            
            children_data.append(child_info)
        
        logger.info(
            f"Driver {request.user} viewed children info for road {road_id}",
            extra={
                "driver_id": request.user,
                "road_id": road_id,
                "children_count": len(children_data),
                "children_with_allergies": sum(1 for c in children_data if c["has_allergies"]),
                "event_type": "driver_children_info_viewed"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Success",
            "children": children_data,
            "count": len(children_data),
            "road_id": road_id
        })
        
    except Exception as e:
        logger.error(
            f"Error getting children info for driver: {str(e)}",
            extra={
                "driver_id": request.user,
                "road_id": road_id,
                "error": str(e),
                "event_type": "driver_children_info_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при получении информации о детях"
        }, 500)


@router.get("/my_children")
async def get_my_children(request: Request):
    """
    BE-MVP-019: Получение информации о всех детях водителя.
    
    Возвращает список всех детей из активных маршрутов водителя.
    Полезно для общего обзора.
    
    Args:
        request: Объект запроса с driver ID
        
    Returns:
        JSONResponse: Информация о всех детях водителя
    """
    try:
        # Получаем все активные маршруты водителя
        driver_roads = await DataScheduleRoadDriver.filter(
            id_driver=request.user,
            isActive=True
        ).values_list("id_schedule_road", flat=True)
        
        if not driver_roads:
            return JSONResponse({
                "status": True,
                "message": "У вас нет активных маршрутов",
                "children": [],
                "count": 0
            })
        
        # Получаем всех детей из этих маршрутов
        road_children = await DataScheduleRoadChild.filter(
            id_schedule_road__in=list(driver_roads),
            isActive=True
        ).values_list("id_child", flat=True)
        
        # Убираем дубликаты
        unique_children = list(set(road_children))
        
        if not unique_children:
            return JSONResponse({
                "status": True,
                "message": "На ваших маршрутах нет детей",
                "children": [],
                "count": 0
            })
        
        # Получаем полную информацию о каждом ребенке
        children_data = []
        for child_id in unique_children:
            child = await UsersChild.filter(id=child_id, isActive=True).first()
            if not child:
                continue
            
            child_info = {
                "id": child.id,
                "name": child.name,
                "surname": child.surname,
                "age": child.age,
                "photo_path": child.photo_path if child.photo_path else not_user_photo,
                "school_class": child.school_class
            }
            
            # Медицинская информация (только критичные поля)
            medical_info = await ChildMedicalInfo.filter(
                id_child=child_id,
                isActive=True
            ).first()
            
            if medical_info:
                child_info["has_allergies"] = bool(medical_info.allergies)
                child_info["allergies"] = medical_info.allergies
                child_info["has_special_needs"] = bool(medical_info.special_needs)
            else:
                child_info["has_allergies"] = False
                child_info["allergies"] = None
                child_info["has_special_needs"] = False
            
            children_data.append(child_info)
        
        logger.info(
            f"Driver {request.user} viewed all children",
            extra={
                "driver_id": request.user,
                "children_count": len(children_data),
                "event_type": "driver_all_children_viewed"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Success",
            "children": children_data,
            "count": len(children_data)
        })
        
    except Exception as e:
        logger.error(
            f"Error getting all children for driver: {str(e)}",
            extra={
                "driver_id": request.user,
                "error": str(e),
                "event_type": "driver_all_children_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при получении информации о детях"
        }, 500)


# ============================================================================
# BE-MVP-021: Верификация водителя
# ============================================================================

@router.post("/generate_meeting_code")
async def generate_meeting_code(request: Request, item: GenerateMeetingCode):
    """
    BE-MVP-021: Генерация кода встречи для водителя.
    
    Водитель генерирует 4-значный код для конкретного маршрута.
    Родитель использует этот код для верификации водителя при передаче ребенка.
    
    Args:
        request: Объект запроса с driver ID
        item: ID маршрута
        
    Returns:
        JSONResponse: Сгенерированный код встречи
    """
    try:
        # Проверяем, что водитель имеет доступ к этому маршруту
        driver_road = await DataScheduleRoadDriver.filter(
            id_schedule_road=item.id_schedule_road,
            id_driver=request.user,
            isActive=True
        ).first()
        
        if not driver_road:
            return JSONResponse({
                "status": False,
                "message": "У вас нет доступа к этому маршруту"
            }, 403)
        
        # Проверяем, есть ли уже активный код для этого маршрута
        from datetime import datetime, timedelta
        existing_code = await DriverMeetingCode.filter(
            id_driver=request.user,
            id_schedule_road=item.id_schedule_road,
            isActive=True,
            is_used=False,
            expires_at__gt=datetime.now()
        ).first()
        
        if existing_code:
            # Возвращаем существующий код
            return JSONResponse({
                "status": True,
                "message": "Активный код уже существует",
                "meeting_code": existing_code.meeting_code,
                "expires_at": existing_code.expires_at.isoformat(),
                "id_schedule_road": item.id_schedule_road
            })
        
        # Генерируем новый 4-значный код
        import random
        meeting_code = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        
        # Код действителен 24 часа
        expires_at = datetime.now() + timedelta(hours=24)
        
        # Создаем запись в БД
        code_record = await DriverMeetingCode.create(
            id_driver=request.user,
            id_schedule_road=item.id_schedule_road,
            meeting_code=meeting_code,
            expires_at=expires_at,
            datetime_create=datetime.now()
        )
        
        logger.info(
            f"Driver {request.user} generated meeting code for road {item.id_schedule_road}",
            extra={
                "driver_id": request.user,
                "road_id": item.id_schedule_road,
                "code_id": code_record.id,
                "event_type": "meeting_code_generated"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Код встречи успешно сгенерирован",
            "meeting_code": meeting_code,
            "expires_at": expires_at.isoformat(),
            "id_schedule_road": item.id_schedule_road
        })
        
    except Exception as e:
        logger.error(
            f"Error generating meeting code: {str(e)}",
            extra={
                "driver_id": request.user,
                "road_id": item.id_schedule_road,
                "error": str(e),
                "event_type": "meeting_code_generation_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при генерации кода встречи"
        }, 500)


@router.post("/verify_meeting_code")
async def verify_meeting_code(request: Request, item: VerifyMeetingCode):
    """
    BE-MVP-021: Верификация кода встречи родителем.
    
    Родитель вводит 4-значный код, который показал водитель.
    Если код правильный и не истек, водитель верифицирован.
    
    Args:
        request: Объект запроса с parent ID
        item: Код встречи и ID маршрута
        
    Returns:
        JSONResponse: Результат верификации
    """
    try:
        from datetime import datetime
        
        # Проверяем, что родитель имеет отношение к этому маршруту
        # Получаем расписание из маршрута
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
                    "event_type": "meeting_code_invalid"
                }
            )
            return JSONResponse({
                "status": False,
                "message": "Неверный код встречи"
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
                "message": "Этот код уже был использован"
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
            "surname": driver.surname
        }
        
        # Получаем фото водителя
        driver_photo = await UsersUserPhoto.filter(id_user=driver.id).first()
        if driver_photo:
            driver_data["photo_path"] = driver_photo.photo_path
        
        logger.info(
            f"Parent {request.user} verified driver {code_record.id_driver} with meeting code",
            extra={
                "parent_id": request.user,
                "driver_id": code_record.id_driver,
                "road_id": item.id_schedule_road,
                "code_id": code_record.id,
                "event_type": "meeting_code_verified"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Водитель успешно верифицирован",
            "driver": driver_data,
            "verified_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(
            f"Error verifying meeting code: {str(e)}",
            extra={
                "parent_id": request.user,
                "road_id": item.id_schedule_road,
                "error": str(e),
                "event_type": "meeting_code_verification_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при верификации кода"
        }, 500)


@router.get("/my_meeting_codes")
async def get_my_meeting_codes(request: Request):
    """
    BE-MVP-021: Получение списка кодов встречи водителя.
    
    Возвращает все активные коды встречи водителя.
    
    Args:
        request: Объект запроса с driver ID
        
    Returns:
        JSONResponse: Список кодов встречи
    """
    try:
        from datetime import datetime
        
        # Получаем все активные коды водителя
        codes = await DriverMeetingCode.filter(
            id_driver=request.user,
            isActive=True,
            expires_at__gt=datetime.now()
        ).order_by("-datetime_create").values(
            "id", "id_schedule_road", "meeting_code", "is_used", 
            "expires_at", "verified_by", "verified_at", "datetime_create"
        )
        
        # Обогащаем данные информацией о маршруте
        for code in codes:
            road = await DataScheduleRoad.filter(id=code["id_schedule_road"]).first()
            if road:
                code["road_title"] = road.title
                code["road_type"] = road.type_drive
            
            # Форматируем даты
            code["expires_at"] = code["expires_at"].isoformat() if code["expires_at"] else None
            code["verified_at"] = code["verified_at"].isoformat() if code["verified_at"] else None
            code["datetime_create"] = code["datetime_create"].isoformat() if code["datetime_create"] else None
        
        return JSONResponse({
            "status": True,
            "message": "Success",
            "codes": codes,
            "count": len(codes)
        })
        
    except Exception as e:
        logger.error(
            f"Error getting meeting codes: {str(e)}",
            extra={
                "driver_id": request.user,
                "error": str(e),
                "event_type": "meeting_codes_get_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при получении кодов встречи"
        }, 500)


# ============================================================================
# BE-MVP-022: Автоуведомления статусов поездки
# ============================================================================

@router.post("/update_trip_status/{order_id}")
async def update_trip_status(request: Request, order_id: int, status_id: int):
    """
    BE-MVP-022: Обновление статуса поездки водителем.
    
    Водитель обновляет статус поездки, родитель автоматически получает push-уведомление.
    
    Статусы:
    - 1: Создан
    - 2: Водитель выехал
    - 3: Водитель прибыл к точке
    - 4: Ребенок в машине
    - 5: Поездка завершена
    
    Args:
        request: Объект запроса с driver ID
        order_id: ID заказа
        status_id: ID нового статуса
        
    Returns:
        JSONResponse: Результат обновления статуса
    """
    try:
        # Получаем заказ
        order = await DataOrder.filter(id=order_id, isActive=True).first()
        
        if not order:
            logger.warning(
                f"Driver {request.user} attempted to update non-existent order {order_id}",
                extra={
                    "driver_id": request.user,
                    "order_id": order_id,
                    "event_type": "trip_status_order_not_found"
                }
            )
            return JSONResponse({
                "status": False,
                "message": "Заказ не найден"
            }, 404)
        
        # Проверяем, что водитель назначен на этот заказ
        if order.id_driver != request.user:
            logger.warning(
                f"Driver {request.user} attempted to update order {order_id} assigned to driver {order.id_driver}",
                extra={
                    "driver_id": request.user,
                    "order_id": order_id,
                    "assigned_driver": order.id_driver,
                    "event_type": "trip_status_access_denied"
                }
            )
            return JSONResponse({
                "status": False,
                "message": "Вы не назначены на этот заказ"
            }, 403)
        
        # Проверяем существование статуса
        status = await DataDrivingStatus.filter(id=status_id).first()
        if not status:
            return JSONResponse({
                "status": False,
                "message": "Статус не найден"
            }, 404)
        
        old_status_id = order.id_status
        
        # Обновляем статус заказа
        await DataOrder.filter(id=order_id).update(id_status=status_id)
        
        # Получаем информацию о родителе
        parent_id = order.id_user
        parent = await UsersUser.filter(id=parent_id).first()
        
        # Определяем текст уведомления
        status_messages = {
            2: {
                "title": "Водитель выехал",
                "body": "Водитель выехал к точке встречи"
            },
            3: {
                "title": "Водитель прибыл",
                "body": "Водитель прибыл к точке встречи"
            },
            4: {
                "title": "Ребенок в машине",
                "body": "Ребенок находится в машине, поездка началась"
            },
            5: {
                "title": "Поездка завершена",
                "body": "Поездка успешно завершена"
            }
        }
        
        # Отправляем push-уведомление родителю
        if status_id in status_messages:
            notification_data = status_messages[status_id]
            
            try:
                await sendPush(
                    user_id=parent_id,
                    title=notification_data["title"],
                    body=notification_data["body"],
                    data={
                        "type": "trip_status_update",
                        "order_id": order_id,
                        "status_id": status_id,
                        "status": status.status
                    }
                )
                
                logger.info(
                    f"Trip status notification sent to parent {parent_id}",
                    extra={
                        "parent_id": parent_id,
                        "driver_id": request.user,
                        "order_id": order_id,
                        "old_status": old_status_id,
                        "new_status": status_id,
                        "event_type": "trip_status_notification_sent"
                    }
                )
            except Exception as e:
                logger.error(
                    f"Failed to send trip status notification: {str(e)}",
                    extra={
                        "parent_id": parent_id,
                        "order_id": order_id,
                        "error": str(e),
                        "event_type": "trip_status_notification_failed"
                    }
                )
        
        # Логируем успешное обновление статуса
        logger.info(
            f"Driver {request.user} updated trip {order_id} status from {old_status_id} to {status_id}",
            extra={
                "driver_id": request.user,
                "order_id": order_id,
                "parent_id": parent_id,
                "old_status": old_status_id,
                "new_status": status_id,
                "status_name": status.status,
                "event_type": "trip_status_updated"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Статус поездки обновлен",
            "order_id": order_id,
            "new_status": {
                "id": status_id,
                "name": status.status
            }
        })
        
    except Exception as e:
        logger.error(
            f"Error updating trip status: {str(e)}",
            extra={
                "driver_id": request.user,
                "order_id": order_id,
                "status_id": status_id,
                "error": str(e),
                "event_type": "trip_status_update_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при обновлении статуса поездки"
        }, 500)


# ============================================================================
# BE-MVP-010: Система выплат водителям
# ============================================================================

def validate_card_luhn(card_number: str) -> bool:
    """
    Валидация номера карты по алгоритму Луна.
    
    Args:
        card_number: Номер карты (строка из цифр)
        
    Returns:
        True если карта валидна, False иначе
    """
    # Убираем пробелы и дефисы
    card_number = card_number.replace(" ", "").replace("-", "")
    
    # Проверяем, что это только цифры
    if not card_number.isdigit():
        return False
    
    # Проверяем длину (обычно 13-19 цифр)
    if len(card_number) < 13 or len(card_number) > 19:
        return False
    
    # Алгоритм Луна
    def luhn_checksum(card_num):
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(card_num)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        return checksum % 10
    
    return luhn_checksum(card_number) == 0


@router.get("/balance")
async def get_driver_balance(request: Request):
    """
    BE-MVP-010: Получение баланса водителя.
    
    Водитель может просмотреть свой текущий баланс и доступные для вывода средства.
    
    Returns:
        JSONResponse: Баланс водителя
    """
    try:
        # Получаем баланс водителя
        balance = await DataUserBalance.filter(
            id_user=request.user,
            isActive=True
        ).first()
        
        if not balance:
            # Создаем баланс если его нет
            balance = await DataUserBalance.create(
                id_user=request.user,
                money=0,
                isActive=True
            )
        
        logger.info(
            f"Driver {request.user} checked balance: {balance.money}",
            extra={
                "driver_id": request.user,
                "balance": float(balance.money),
                "event_type": "driver_balance_checked"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Success",
            "balance": float(balance.money),
            "currency": "RUB"
        })
        
    except Exception as e:
        logger.error(
            f"Error getting driver balance: {str(e)}",
            extra={
                "driver_id": request.user,
                "error": str(e),
                "event_type": "driver_balance_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при получении баланса"
        }, 500)


@router.post("/withdraw")
async def request_withdrawal(request: Request, amount: float, card_number: str):
    """
    BE-MVP-010: Запрос на вывод средств водителем.
    
    Водитель может запросить вывод средств на свою карту.
    Минимальная сумма вывода: 500 руб.
    Номер карты валидируется по алгоритму Луна.
    
    Args:
        request: Объект запроса с driver ID
        amount: Сумма для вывода
        card_number: Номер карты для вывода
        
    Returns:
        JSONResponse: Результат запроса на вывод
    """
    try:
        MIN_WITHDRAWAL = 500  # Минимальная сумма вывода
        
        # Валидация суммы
        if amount < MIN_WITHDRAWAL:
            logger.warning(
                f"Driver {request.user} attempted withdrawal below minimum: {amount}",
                extra={
                    "driver_id": request.user,
                    "amount": amount,
                    "min_amount": MIN_WITHDRAWAL,
                    "event_type": "withdrawal_below_minimum"
                }
            )
            return JSONResponse({
                "status": False,
                "message": f"Минимальная сумма вывода: {MIN_WITHDRAWAL} руб"
            }, 400)
        
        # Валидация номера карты по алгоритму Луна
        if not validate_card_luhn(card_number):
            logger.warning(
                f"Driver {request.user} provided invalid card number",
                extra={
                    "driver_id": request.user,
                    "event_type": "withdrawal_invalid_card"
                }
            )
            return JSONResponse({
                "status": False,
                "message": "Неверный номер карты"
            }, 400)
        
        # Получаем баланс водителя
        balance = await DataUserBalance.filter(
            id_user=request.user,
            isActive=True
        ).first()
        
        if not balance or balance.money < amount:
            current_balance = float(balance.money) if balance else 0
            logger.warning(
                f"Driver {request.user} insufficient balance for withdrawal",
                extra={
                    "driver_id": request.user,
                    "requested_amount": amount,
                    "current_balance": current_balance,
                    "event_type": "withdrawal_insufficient_balance"
                }
            )
            return JSONResponse({
                "status": False,
                "message": f"Недостаточно средств. Доступно: {current_balance} руб"
            }, 400)
        
        # Создаем запрос на вывод средств
        from datetime import datetime
        withdrawal_request = await HistoryRequestPayment.create(
            id_user=request.user,
            id_card=0,  # Временно, пока не привязываем карту
            id_history=0,  # Будет обновлено после обработки
            money=amount,
            isCashback=False,
            isSuccess=False,  # Будет обновлено после обработки
            isActive=True,
            datetime_create=datetime.now()
        )
        
        # Резервируем средства (вычитаем из баланса)
        new_balance = float(balance.money) - amount
        await DataUserBalance.filter(id=balance.id).update(money=new_balance)
        
        # Логируем создание запроса
        logger.info(
            f"Driver {request.user} requested withdrawal of {amount} RUB",
            extra={
                "driver_id": request.user,
                "amount": amount,
                "card_last_4": card_number[-4:],
                "withdrawal_id": withdrawal_request.id,
                "new_balance": new_balance,
                "event_type": "withdrawal_requested"
            }
        )
        
        # Отправляем уведомление водителю
        try:
            await sendPush(
                user_id=request.user,
                title="Запрос на вывод средств",
                body=f"Ваш запрос на вывод {amount} руб принят в обработку",
                data={
                    "type": "withdrawal_requested",
                    "withdrawal_id": withdrawal_request.id,
                    "amount": amount
                }
            )
        except Exception as e:
            logger.error(
                f"Failed to send withdrawal notification: {str(e)}",
                extra={
                    "withdrawal_id": withdrawal_request.id,
                    "error": str(e),
                    "event_type": "withdrawal_notification_failed"
                }
            )
        
        return JSONResponse({
            "status": True,
            "message": "Запрос на вывод средств принят",
            "withdrawal_id": withdrawal_request.id,
            "amount": amount,
            "new_balance": new_balance,
            "status_text": "В обработке"
        })
        
    except Exception as e:
        logger.error(
            f"Error processing withdrawal request: {str(e)}",
            extra={
                "driver_id": request.user,
                "amount": amount,
                "error": str(e),
                "event_type": "withdrawal_request_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при создании запроса на вывод"
        }, 500)
