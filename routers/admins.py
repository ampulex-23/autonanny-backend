import os

from const.static_data_const import not_user_photo, not_found_other_parametr,OtherDriveParametr,UpdateOtherDriveParametr
from models.authentication_db import UsersUserAccount, UsersReferalCode, UsersAuthorizationData, UsersBearerToken
from models.orders_db import DataSchedule, DataScheduleRoad, DataScheduleRoadAddress, \
    DataScheduleRoadContact, DataScheduleRoadChild
from models.users_db import UsersVerifyAccount, UsersUserPhoto, UsersReferalUser, \
    UsersFranchiseUser, UsersChild
from models.users_db import HistoryPaymentTink, UsersUser
from const.login_const import uncorrect_phone, user_already_creates, error_create_user
from defs import check_correct_phone, error, get_date_from_datetime
from models.chats_db import ChatsChatParticipant, ChatsChat
from models.static_data_db import DataOtherDriveParametr, PricingCoefficients
from models.admins_db import AdminMobileSettings
from models.drivers_db import UsersDriverData
from sevice.admin_service import ReportMaker, create_franchise_user, create_partner_user

from common.logger import logger
from config import settings

from fastapi.responses import FileResponse
from fastapi import APIRouter, Request, Depends
from starlette.background import BackgroundTask
from const.admins_const import *
from models.users_db import ChildEmergencyContact
from tortoise.models import Q
from tortoise import Tortoise
from smsaero import SmsAero
import traceback
import decimal
import json
from utils.response_helpers import generate_responses

router = APIRouter()
router_for_franchise_admin = APIRouter()

@router.post("/new_user",
             responses=generate_responses([success_answer,
                                           uncorrect_phone,
                                           user_already_creates,
                                           unsupported_role,
                                           new_user_message_dont_delivery,
                                           error_create_user]))
async def new_user(item: NewUser):
    item.phone = await check_correct_phone(item.phone)
    if item.phone is None: return uncorrect_phone
    if await UsersUser.filter(phone=item.phone).count()>0:
        return user_already_creates
    if item.role not in [3, 4, 5, 6]:
        return unsupported_role
    if item.role == 5:
        try:
            await create_partner_user(item)
        except:
            logger.error("Can't create user in DB")
            return error_create_user
    else:
        try:
            await create_franchise_user(item)
        except Exception:
            logger.error("Can't create user in DB")
            return error_create_user

    try:
        api = SmsAero(settings.sms_aero_email, settings.sms_aero_api_key)
        api.send(item.phone, f"Ваши данные для входа в аккаунт АвтоНяни:\n\n"
                                 f"Логин: {item.phone}\n"
                                 f"Пароль: {item.password}\n")
    except Exception:
        await error(traceback.format_exc())
        return new_user_message_dont_delivery
    return success_answer

@router.get("/franchise_admins")
async def get_franchise_admins() -> SuccessGetFranchiseAdmins:
    """
    Возвращает информацию об администраторах франшизы
    """
    response_data = {}

    SQL_REQUEST = ('SELECT u.id, u.phone, fc.id_city, c.title FROM "users".user AS u '
                   'JOIN "users".user_account AS ua ON u.id=ua.id_user '
                   'JOIN "users".franchise_user as fu ON u.id=fu.id_user '
                   'LEFT JOIN "users".franchise_city fc ON fu.id_franchise=fc.id_franchise '
                   'LEFT JOIN "data".city as c ON fc.id_city=c.id '
                   'WHERE ua.id_type_account=6;')
    #users = await UsersUser.filter(user_accounts__id_type_account="6").all().values("id", "phone", "franchise_users__id_franchise__franchise_cities__id_city__id", "franchise_users__id_franchise__franchise_cities__id_city__title")
    conn = Tortoise.get_connection("default")
    users = await conn.execute_query_dict(SQL_REQUEST)
    logger.debug(users)
    for user in users:
        if user["id"] not in users: #user_id key help to add double row with cities
            try:
                response_data[user["id"]] = FranchiseAdmin(
                    id= user["id"],
                    phone= user["phone"],
                    cities=[City(
                        id= user["id_city"],
                        title= user["title"]
                    )] if user["id_city"] else None
                )
            except Exception:
                logger.error(f"Row: {user} has incorrect format")
        else:
            try:
                response_data[user["id"]].cities.append(City(
                    id=user["id_city"],
                    title=user["title"]
                ))
            except Exception:
                logger.error(f"Row: {user} has incorrect format")
    logger.debug(response_data)
    validate=FranchiseAdmins(response_data.values())
    return SuccessGetFranchiseAdmins(franchise_admins=validate)

"""
@router.post("/get_partners",
             responses=generate_responses([get_partners]))
async def get_partners(item: Union[GetPartners, None] = None):
    if item is not None:
        data = await UsersUserAccount.filter(id_type_account=5).order_by("-id").offset(item.offset).limit(item.limit).values()
    else:
        data = await UsersUserAccount.filter(id_type_account=2).order_by("-id").all().values()
    users = []
    for ids in data:
        users.append(ids["id_user"])
    result = await UsersUser.filter(id__in=users).order_by("-id").all().values()
    for partner in result:
        photo = await UsersUserPhoto.filter(id_user=partner["id"]).first().values()
        photo = not_user_photo if photo is None or "photo_path" not in photo else photo["photo_path"]
        partner["photo_path"] = photo
        partner["datetime_create"] = await get_date_from_datetime(partner["datetime_create"])
        del partner["phone"]
    partners = []
    if item is not None and item.search is not None:
        for partner in result:
            if (partner["name"] is not None and partner["surname"] is not None) and \
                (item.search.lower() in partner["name"].lower() or item.search.lower() == partner["name"].lower() or
                item.search.lower() in partner["surname"].lower() or item.search.lower() == partner["surname"].lower()):
                partners.append(partner)
    return JSONResponse({"status": True,
                         "message": "Success!",
                         "partners": partners})
"""

@router.post("/get_partners",
             responses=generate_responses([get_partners]))
async def get_partners(item: Union[GetPartners, None] = None):
    SQL_REQUEST = ('SELECT u.id, u.surname, u.name, u.datetime_create, u.phone, ua.id_type_account FROM users.user AS u '
                   'LEFT JOIN users.user_account AS ua ON u.id=ua.id_user '
                   'INNER JOIN users.referal_code AS rc ON u.id=rc.id_user '
                   'WHERE ua.id_type_account=5 '
                   f'LIMIT {item.limit} OFFSET {item.offset};')
    conn = Tortoise.get_connection("default")
    logger.debug(SQL_REQUEST)
    users = await conn.execute_query_dict(SQL_REQUEST)
    logger.debug(users)
    for partner in users:
        photo = await UsersUserPhoto.filter(id_user=partner["id"]).first().values()
        photo = not_user_photo if photo is None or "photo_path" not in photo else photo["photo_path"]
        partner["photo_path"] = photo
        partner["datetime_create"] = await get_date_from_datetime(partner["datetime_create"])
        partner["role"] = [partner["id_type_account"]]
        del partner["id_type_account"]
        del partner["phone"]
    partners = []
    if item is not None and item.search is not None:
        for partner in users:
            if (partner["name"] is not None and partner["surname"] is not None) and \
                (item.search.lower() in partner["name"].lower() or item.search.lower() == partner["name"].lower() or
                item.search.lower() in partner["surname"].lower() or item.search.lower() == partner["surname"].lower()):
                partners.append(partner)
    return JSONResponse({"status": True,
                         "message": "Success!",
                         "partners": partners})

@router.post("/get_partner",
             responses=generate_responses([partner_not_found, get_partner]))
async def get_partner_by_id(item: GetPartner):
    if await UsersUser.filter(id=item.id).count() == 0 or \
            await UsersUserAccount.filter(id_user=item.id, id_type_account=5).count() == 0:
        return partner_not_found
    data = await UsersUser.filter(id=item.id).first().values()
    refer = await UsersReferalCode.filter(id_user=item.id).first().values()
    photo = await UsersUserPhoto.filter(id_user=item.id).first().values()
    photo = photo["photo_path"] if photo is not None and "photo_path" in photo else not_user_photo
    referals = await UsersReferalUser.filter(id_user=item.id).order_by("-id").all().values()
    for ref in referals:
        refer_data = await UsersUser.filter(id=ref["id_user_referal"]).first().values()
        ref_roles = await UsersUserAccount.filter(id_user=ref["id_user_referal"]).values("id_type_account")
        ref["name"] = refer_data["name"]
        ref["surname"] = refer_data["surname"]
        ref["date_reg"] = await get_date_from_datetime(refer_data["datetime_create"])
        ref["role"] = [next(iter(role.values())) for role in ref_roles] # get values from list of dictonaries
        logger.debug(ref["role"])
        del ref["datetime_create"]
        del ref["id"]
        del ref["id_user"]
        ref["id"] = ref["id_user_referal"]
    return JSONResponse({"status": True,
                         "message": "Success!",
                         "partner": {
                             "name": data["name"],
                             "surname": data["surname"],
                             "phone": data["phone"],
                             "photo_path": photo,
                             "referal_code": refer["code"],
                             "referal_percent": refer["percent"],
                             "referals": referals
                         }})

@router.post("/get_partners_referal",
             responses=generate_responses([partners_referal_not_found, get_partners_referal]))
async def get_partners_referal_by_id(item: GetPartner):
    if await UsersReferalUser.filter(id_user_referal=item.id).count() == 0 or \
        await UsersUserAccount.filter(id_user=item.id, id_type_account=2).count()==0 or\
         await UsersUser.filter(id=item.id).count() == 0:
        return partners_referal_not_found
    user = await UsersUser.filter(id=item.id).first().values()
    photo = await UsersUserPhoto.filter(id_user=item.id).first().values()
    photo = photo["photo_path"] if photo is not None and "photo_path" in photo else not_user_photo
    partner = await UsersReferalUser.filter(id_user_referal=item.id).first().values()
    partner = await UsersReferalCode.filter(id_user=partner["id_user"]).first().values()
    return JSONResponse({"status": True,
                         "message": "Success!",
                         "data": {
                             "name": user["name"],
                             "surname": user["surname"],
                             "date_reg": await get_date_from_datetime(user["datetime_create"]),
                             "phone": user["phone"],
                             "photo_path": photo,
                             "partner_percent": partner["percent"]
                         }})

@router.post("/get_users",
             responses=generate_responses([get_users]))
async def get_all_user(item: GetUsers):
    total, result, data = 0, [], UsersUser.filter(id__not=-1, isActive__in=[False, True]).order_by("-id")
    total = await UsersUser.filter(id__not=-1, isActive__in=[False, True]).count()
    if item is not None:
        data = UsersUser.filter(id__not=-1, isActive__in=[False, True])
        total = await data.count()
        data = data.filter(Q(name__icontains=item.search)|Q(surname__icontains=item.search)|Q(phone__icontains=item.search))
        data = data.offset(item.offset).limit(item.limit)
    data = await data.all().values()
    for user in data:
        photo = await UsersUserPhoto.filter(id_user=user["id"]).first().values()
        photo = not_user_photo if photo is None or "photo_path" not in photo else photo["photo_path"]
        user["photo_path"] = photo
        role = [x["id_type_account"] for x in (await UsersUserAccount.filter(id_user=user["id"]).all().values())]
        roles = []
        if 1 in role:
            roles.append("Родитель")
        if 2 in role:
            roles.append("Водитель")
        if 3 in role:
            roles.append("Оператор")
        if 4 in role:
            roles.append("Менеджер")
        if 5 in role:
            roles.append("Партнёр")
        if 6 in role:
            roles.append("Администратор франшизы")
        if 7 in role:
            roles.append("Администратор")
        user["role"] = roles
        user["status"] = "Активен" if user["isActive"] is True else "Заблокирован"
        user["datetime_create"] = await get_date_from_datetime(user["datetime_create"])
        del user["isActive"]
    return JSONResponse({"status": True,
                         "message": "Success!",
                         "users": data,
                         "total": total})

@router.get("/get_user_children")
async def get_user_children(request: Request, user_id: int):
    """
    Получить список детей пользователя.

    Args:
        request (Request): Запрос.
        user_id (int): ID пользователя-родителя.

    Returns:
        JSONResponse: Ответ в формате JSON с данными детей.
    """
    # Проверяем существование пользователя
    if not await UsersUser.filter(id=user_id, isActive=True).exists():
        return JSONResponse(
            {"status": False, "message": "User not found or inactive"},
            status_code=404
        )

    # Получаем всех активных детей пользователя
    children = await UsersChild.filter(
        id_user=user_id,
        isActive=True
    ).order_by("-datetime_create").values(
        "id",
        "surname",
        "name",
        "patronymic",
        "child_phone",
    )

    return JSONResponse({
        "status": True,
        "message": "Success",
        "data": children,
        "count": len(children)
    })

@router.get("/get_extended_client_info")
async def get_extended_client_info(request: Request, user_id: int):
    """
    Получить расширенную информацию о пользователе:
        - Информация о родителе
        - Информация о детях (с привязанными локациями)
        - Локации без привязки к детям

    Args:
        request (Request): Запрос.
        user_id (int): ID пользователя.

    Returns:
        JSONResponse: Ответ в формате JSON с полной информацией о пользователе.
    """
    # Проверяем существование пользователя
    if not await UsersUser.filter(id=user_id, isActive=True).exists():
        return JSONResponse(
            {"status": False, "message": "User not found or inactive"},
            status_code=404
        )

    user_info = await UsersUser.filter(id=user_id).first().values(
        "id",
        "name",
        "surname",
        "phone",
    )

    children = await UsersChild.filter(
        id_user=user_id,
        isActive=True
    ).order_by("-datetime_create").values(
        "id",
        "surname",
        "name",
        "patronymic",
        "child_phone",
        "age",
    )

    user_photopath = await UsersUserPhoto.filter(id_user=user_id).first().values(
        "photo_path")
    user_info["photo_path"] = user_photopath[
        "photo_path"] if user_photopath is not None and "photo_path" in user_photopath else not_user_photo

    # =================== Получаем инфо о локациях ===================
    user_schedules = await DataSchedule.filter(
        id_user=user_id,
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

@router_for_franchise_admin.post(
    "/ban-user",
    responses=generate_responses([success_answer, user_not_found])
)
async def ban_user(item: GetUser, request: Request):
    """
    Блокирует/разблокирует пользователя в зависимости от его текущего статуса.

    Этот эндпоинт управляет блокировкой и снятием блокировки пользователей. Когда пользователя
    блокируют, — его учетная запись деактивируется, а связанные с ней данные, такие как участие в чате и
    данные водителя обновляются соответствующим образом.
    Если пользователь уже заблокирован, это действие отменяет запрет и повторно активирует
    учетную запись и связанные с ней данные.

    Args:
        item (GetUser): {"id": 1} - ID пользователя, которого нужно заблокировать/разблокировать.
        request (Request): Объект запроса

    Returns:
        JSONResponse - ответ, содержащий статус и сообщение операции.
    """
    if request.user == item.id:
        return JSONResponse(
            {"status": False, "message": "Can't delete main admin!"}, 404
        )
    type_account = await UsersUserAccount.filter(id_user=item.id).first().values()
    if type_account is None:
        return user_not_found
    if type_account["id_type_account"] == 6:
        req_user_franchise = await UsersFranchiseUser.filter(id_user=request.user).first().values()
        req_user_franchise_id = req_user_franchise["id_franchise"]
        ban_user_franchise = await UsersFranchiseUser.filter(id_user=item.id).first().values()
        ban_user_franchise_id = ban_user_franchise["id_franchise"]
        if req_user_franchise_id != ban_user_franchise_id:
            return JSONResponse({"status": False, "message": "You don't have access to this user!"}, 404)
    user = await UsersUser.filter(id=item.id).first().values()
    if user is None:
        return user_not_found
    if await UsersUser.filter(id=item.id, isActive=False).count() > 0:
        await UsersUser.filter(id=item.id).update(isActive=True)
        await UsersVerifyAccount.create(id_user=item.id)
        if await UsersDriverData.filter(id_driver=item.id).count() > 0:
            await UsersDriverData.filter(id_driver=item.id).update(isActive=True)
        chats = [
            x["id_chat"]
            for x in (await ChatsChatParticipant.filter(id_user=item.id).all().values())
        ]
        for each in chats:
            await ChatsChat.filter(id=each).update(isActive=True)

    else:
        await UsersUser.filter(id=item.id).update(isActive=False)
        await UsersVerifyAccount.filter(id_user=item.id).delete()
        await UsersBearerToken.filter(id_user=item.id).delete()
        chats = [
            x["id_chat"]
            for x in (await ChatsChatParticipant.filter(id_user=item.id).all().values())
        ]
        for each in chats:
            await ChatsChat.filter(id=each).update(isActive=False)
        if await UsersDriverData.filter(id_driver=item.id).count() > 0:
            await UsersDriverData.filter(id_driver=item.id).update(isActive=False)
    return success_answer

@router.post("/delete-user",
             responses=generate_responses([success_answer, user_not_found]))
async def delete_user(item: GetUser, request: Request):
    if request.user == item.id:
        return JSONResponse({"status": False, "message": "Can't delete main admin!"}, 404)
    user = await UsersUser.filter(id=item.id).first().values()
    if user is None:
        return user_not_found
    try:
        await UsersUser.filter(id=item.id).update(isActive=None, phone=user["phone"]+"__delete")
    except Exception:
        pass
    chats = [x["id_chat"] for x in (await ChatsChatParticipant.filter(id_user=item.id).all().values())]
    for each in chats:
        await ChatsChat.filter(id=each).update(isActive=False)
    await UsersAuthorizationData.filter(id_user=item.id).delete()
    await UsersBearerToken.filter(id_user=item.id).delete()
    if await UsersDriverData.filter(id_driver=item.id).count() > 0:
        await UsersDriverData.filter(id_driver=item.id).update(isActive=False)
    return success_answer

@router.get("/change-biometry-settings",
            responses=generate_responses([success_answer]))
async def change_state_of_activity_biometry_settings():
    settings = await AdminMobileSettings.filter().order_by("-id").first().values()
    if settings["biometry"] is True:
        await AdminMobileSettings.filter(id=settings["id"]).update(biometry=False)
    else:
        await AdminMobileSettings.filter(id=settings["id"]).update(biometry=True)
    return success_answer

@router.delete("/other-parametrs-of-drive",
               responses=generate_responses([success_answer, not_found_other_parametr]))
async def delete_other_parametr_of_drive(item: GetUser):
    if await DataOtherDriveParametr.filter(isActive=True, id=item.id).count() == 0:
        return not_found_other_parametr
    await DataOtherDriveParametr.filter(isActive=True, id=item.id).update(isActive=False)
    return success_answer

@router.put("/other-parametrs-of-drive",
            responses=generate_responses([success_answer, not_found_other_parametr]))
async def update_other_parametr_of_drive(item: UpdateOtherDriveParametr):
    if await DataOtherDriveParametr.filter(isActive=True, id=item.id).count() == 0:
        return not_found_other_parametr
    if item.title is not None and len(item.title) > 0:
        await DataOtherDriveParametr.filter(isActive=True, id=item.id).update(title=item.title)
    if item.amount is not None and len(str(item.amount)) > 0:
        await DataOtherDriveParametr.filter(isActive=True, id=item.id).update(amount=decimal.Decimal(item.amount))
    return success_answer

@router.post("/other-parametrs-of-drive",
             responses=generate_responses([success_answer]))
async def create_other_parametr_of_drive(item: OtherDriveParametr):
    await DataOtherDriveParametr.create(title=item.title, amount=decimal.Decimal(item.amount))
    return success_answer

@router.get("/report_sales")
async def get_report_sales(request: Request, start_date: date, end_date: date) -> SuccessGetSalary:
    reporter = ReportMaker(HistoryPaymentTink, "Salary", report_type="sum")
    report = await reporter.create_report_by_period(start_date, end_date)
    salary = Report(report)
    response = SuccessGetSalary(salary=salary)
    return response

@router.post("/report_sales",
             responses=generate_responses([]),
             response_class=FileResponse)
async def get_file_report_sales(request: Request, start_date: date, end_date: date):
    reporter = ReportMaker(HistoryPaymentTink, "Salary", report_type="sum")
    await reporter.create_report_by_period(start_date, end_date)
    report_file_path = await reporter.save_report_to_pdf(title="salary_report")
    _, file_name = report_file_path.rsplit('/', 1)
    return FileResponse(report_file_path, media_type="application/pdf", filename=file_name, background=BackgroundTask(os.remove, report_file_path))

@router.get("/report_users")
async def get_report_users(request: Request, start_date: date, end_date: date) -> SuccessGetUserReport:
    try:
        reporter = ReportMaker(UsersUser, "User register", report_type="count")
        report = await reporter.create_report_by_period(start_date, end_date)
        users = Report(report)
    except:
        logger.error("Can't to create report")
    else:
        response = SuccessGetUserReport(user_report=users)
        return response

@router.post("/report_users",
             responses=generate_responses([]),
             response_class=FileResponse)
async def get_file_report_users(request: Request, start_date: date, end_date: date):
    try:
        reporter = ReportMaker(UsersUser, "User register", report_type="count")
        await reporter.create_report_by_period(start_date, end_date)
        report_file_path = await reporter.save_report_to_pdf(title="user_report")
        _, file_name = report_file_path.rsplit('/', 1)
    except:
        logger.error("Can't to create report and report file")
    else:
        return FileResponse(report_file_path, media_type="application/pdf", filename=file_name, background=BackgroundTask(os.remove, report_file_path))


# ============================================================================
# BE-MVP-023: Модуль управления родителями в админ-панели
# ============================================================================

@router.post("/parents")
async def get_parents_list(request: Request, filters: GetParents):
    """
    BE-MVP-023: Получение списка родителей с фильтрацией.
    
    Возвращает список родителей с информацией:
    - Базовая информация (имя, фамилия, телефон, фото)
    - Количество детей
    - Количество активных заказов
    - Статус аккаунта
    - Дата регистрации
    
    Args:
        request: Объект запроса
        filters: Фильтры для поиска и пагинации
        
    Returns:
        JSONResponse: Список родителей с метаданными
    """
    try:
        # Базовый запрос: получаем всех пользователей с ролью "Родитель" (id_type_account=1)
        parent_ids_query = UsersUserAccount.filter(id_type_account=1).values_list("id_user", flat=True)
        parent_ids = await parent_ids_query
        
        # Строим запрос к пользователям
        query = UsersUser.filter(id__in=parent_ids)
        
        # Фильтр по статусу активности
        if filters.is_active is not None:
            query = query.filter(isActive=filters.is_active)
        
        # Поиск по имени, фамилии, телефону
        if filters.search:
            query = query.filter(
                Q(name__icontains=filters.search) |
                Q(surname__icontains=filters.search) |
                Q(phone__icontains=filters.search)
            )
        
        # Подсчет общего количества
        total = await query.count()
        
        # Пагинация
        parents = await query.order_by("-datetime_create").offset(filters.offset).limit(filters.limit).values(
            "id", "name", "surname", "phone", "isActive", "datetime_create"
        )
        
        # Обогащаем данные
        result = []
        for parent in parents:
            # Фото пользователя
            photo = await UsersUserPhoto.filter(id_user=parent["id"]).first()
            parent["photo_path"] = photo.photo_path if photo and photo.photo_path else not_user_photo
            
            # Количество детей
            children_count = await UsersChild.filter(id_user=parent["id"], isActive=True).count()
            parent["children_count"] = children_count
            
            # Количество активных заказов
            active_orders = await DataSchedule.filter(id_user=parent["id"], isActive=True).count()
            parent["active_orders_count"] = active_orders
            
            # Фильтр по наличию детей
            if filters.has_children is not None:
                if filters.has_children and children_count == 0:
                    continue
                if not filters.has_children and children_count > 0:
                    continue
            
            # Фильтр по наличию активных заказов
            if filters.has_active_orders is not None:
                if filters.has_active_orders and active_orders == 0:
                    continue
                if not filters.has_active_orders and active_orders > 0:
                    continue
            
            # Форматируем дату
            parent["datetime_create"] = await get_date_from_datetime(parent["datetime_create"])
            parent["status"] = "Активен" if parent["isActive"] else "Заблокирован"
            
            result.append(parent)
        
        logger.info(
            f"Admin {request.user} requested parents list",
            extra={
                "admin_id": request.user,
                "total_found": len(result),
                "filters": filters.dict(),
                "event_type": "admin_parents_list_viewed"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Success",
            "parents": result,
            "total": total,
            "offset": filters.offset,
            "limit": filters.limit
        })
        
    except Exception as e:
        logger.error(
            f"Error getting parents list: {str(e)}",
            extra={
                "admin_id": request.user,
                "error": str(e),
                "event_type": "admin_parents_list_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при получении списка родителей"
        }, 500)


@router.get("/parents/{parent_id}")
async def get_parent_profile(request: Request, parent_id: int):
    """
    BE-MVP-023: Получение детальной карточки профиля родителя.
    
    Возвращает полную информацию о родителе:
    - Личные данные
    - Список детей с их данными
    - Экстренные контакты детей
    - Активные и завершенные заказы
    - История платежей
    - Баланс
    
    Args:
        request: Объект запроса
        parent_id: ID родителя
        
    Returns:
        JSONResponse: Детальная информация о родителе
    """
    try:
        # Проверяем, что пользователь существует и является родителем
        parent_account = await UsersUserAccount.filter(id_user=parent_id, id_type_account=1).first()
        if not parent_account:
            return JSONResponse({
                "status": False,
                "message": "Родитель не найден"
            }, 404)
        
        # Получаем базовую информацию о родителе
        parent = await UsersUser.filter(id=parent_id).first()
        if not parent:
            return JSONResponse({
                "status": False,
                "message": "Пользователь не найден"
            }, 404)
        
        parent_data = {
            "id": parent.id,
            "name": parent.name,
            "surname": parent.surname,
            "phone": parent.phone,
            "isActive": parent.isActive,
            "datetime_create": await get_date_from_datetime(parent.datetime_create)
        }
        
        # Фото
        photo = await UsersUserPhoto.filter(id_user=parent_id).first()
        parent_data["photo_path"] = photo.photo_path if photo and photo.photo_path else not_user_photo
        
        # Баланс
        balance = await UsersUser.filter(id=parent_id).first().values("balance")
        parent_data["balance"] = float(balance["balance"]) if balance else 0.0
        
        # Получаем детей
        children = await UsersChild.filter(id_user=parent_id, isActive=True).order_by("-datetime_create").values(
            "id", "name", "surname", "patronymic", "age", "birthday", "gender", 
            "school_class", "character_notes", "photo_path"
        )
        
        # Для каждого ребенка получаем экстренные контакты и медицинскую информацию
        for child in children:
            emergency_contacts = await ChildEmergencyContact.filter(
                id_child=child["id"],
                isActive=True
            ).order_by("priority").values(
                "id", "name", "relationship", "phone", "priority", "notes"
            )
            child["emergency_contacts"] = emergency_contacts
            child["emergency_contacts_count"] = len(emergency_contacts)
            
            # BE-MVP-017: Получаем медицинскую информацию
            from models.users_db import ChildMedicalInfo
            medical_info = await ChildMedicalInfo.filter(
                id_child=child["id"],
                isActive=True
            ).first()
            
            if medical_info:
                child["medical_info"] = {
                    "allergies": medical_info.allergies,
                    "chronic_diseases": medical_info.chronic_diseases,
                    "medications": medical_info.medications,
                    "blood_type": medical_info.blood_type,
                    "special_needs": medical_info.special_needs,
                    "has_medical_info": True
                }
            else:
                child["medical_info"] = None
                child["has_medical_info"] = False
        
        parent_data["children"] = children
        parent_data["children_count"] = len(children)
        
        # Получаем активные заказы
        active_orders = await DataSchedule.filter(
            id_user=parent_id,
            isActive=True
        ).order_by("-datetime_create").values(
            "id", "datetime_create", "datetime_end"
        )
        
        # Для каждого заказа получаем маршруты
        for order in active_orders:
            roads = await DataScheduleRoad.filter(
                id_schedule=order["id"],
                isActive=True
            ).count()
            order["roads_count"] = roads
            order["datetime_create"] = await get_date_from_datetime(order["datetime_create"])
            if order["datetime_end"]:
                order["datetime_end"] = await get_date_from_datetime(order["datetime_end"])
        
        parent_data["active_orders"] = active_orders
        parent_data["active_orders_count"] = len(active_orders)
        
        # История платежей (последние 10)
        payments = await HistoryPaymentTink.filter(
            id_user=parent_id
        ).order_by("-datetime_create").limit(10).values(
            "id", "amount", "status", "datetime_create"
        )
        
        for payment in payments:
            payment["datetime_create"] = await get_date_from_datetime(payment["datetime_create"])
            payment["amount"] = float(payment["amount"])
        
        parent_data["recent_payments"] = payments
        parent_data["payments_count"] = len(payments)
        
        logger.info(
            f"Admin {request.user} viewed parent profile {parent_id}",
            extra={
                "admin_id": request.user,
                "parent_id": parent_id,
                "event_type": "admin_parent_profile_viewed"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Success",
            "parent": parent_data
        })
        
    except Exception as e:
        logger.error(
            f"Error getting parent profile: {str(e)}",
            extra={
                "admin_id": request.user,
                "parent_id": parent_id,
                "error": str(e),
                "event_type": "admin_parent_profile_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при получении профиля родителя"
        }, 500)


@router.post("/parents/contact")
async def contact_parent(request: Request, item: ContactParent):
    """
    BE-MVP-023: Инициация связи с родителем.
    
    Создает запись о попытке связи администратора с родителем.
    В зависимости от типа связи:
    - call: Логирует намерение позвонить
    - sms: Отправляет SMS (если интегрирован SMS-сервис)
    - push: Отправляет Push-уведомление
    
    Args:
        request: Объект запроса
        item: Данные для связи (ID родителя, тип, сообщение)
        
    Returns:
        JSONResponse: Статус операции
    """
    try:
        # Проверяем существование родителя
        parent = await UsersUser.filter(id=item.parent_id).first()
        if not parent:
            return JSONResponse({
                "status": False,
                "message": "Родитель не найден"
            }, 404)
        
        # Проверяем, что это действительно родитель
        is_parent = await UsersUserAccount.filter(id_user=item.parent_id, id_type_account=1).exists()
        if not is_parent:
            return JSONResponse({
                "status": False,
                "message": "Пользователь не является родителем"
            }, 400)
        
        contact_info = {
            "admin_id": request.user,
            "parent_id": item.parent_id,
            "parent_phone": parent.phone,
            "contact_type": item.contact_type,
            "message": item.message
        }
        
        if item.contact_type == "push":
            # Отправляем Push-уведомление
            fbid = await UsersBearerToken.filter(id_user=item.parent_id).order_by("-id").first()
            if fbid:
                from defs import sendPush
                await sendPush(
                    fbid.fbid,
                    "Сообщение от администратора",
                    item.message or "Администратор хочет с вами связаться",
                    {"action": "admin_contact"}
                )
                contact_info["push_sent"] = True
            else:
                contact_info["push_sent"] = False
                contact_info["push_error"] = "Firebase token not found"
        
        elif item.contact_type == "sms":
            # TODO: Интеграция с SMS-сервисом
            contact_info["sms_sent"] = False
            contact_info["sms_note"] = "SMS integration not implemented yet"
        
        elif item.contact_type == "call":
            # Просто логируем намерение позвонить
            contact_info["call_logged"] = True
        
        logger.info(
            f"Admin {request.user} initiated contact with parent {item.parent_id}",
            extra={
                **contact_info,
                "event_type": "admin_parent_contact_initiated"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": f"Связь с родителем инициирована ({item.contact_type})",
            "parent_phone": parent.phone,
            "contact_type": item.contact_type
        })
        
    except Exception as e:
        logger.error(
            f"Error contacting parent: {str(e)}",
            extra={
                "admin_id": request.user,
                "parent_id": item.parent_id,
                "error": str(e),
                "event_type": "admin_parent_contact_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при инициации связи с родителем"
        }, 500)


# ============================================================================
# BE-MVP-024: Управление контрактами родителей
# ============================================================================

@router.post("/schedules")
async def get_all_schedules(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    status: str = None,
    parent_id: int = None,
    search: str = None
):
    """
    BE-MVP-024: Получение списка всех контрактов/расписаний для админа.
    
    Админ может просматривать все контракты с фильтрацией и поиском.
    
    Args:
        request: Объект запроса
        page: Номер страницы (по умолчанию 1)
        per_page: Количество на странице (по умолчанию 20)
        status: Фильтр по статусу (active/inactive)
        parent_id: Фильтр по ID родителя
        search: Поиск по названию контракта
        
    Returns:
        JSONResponse: Список контрактов с пагинацией
    """
    try:
        # Строим запрос с фильтрами
        query = DataSchedule.filter()
        
        # Фильтр по статусу
        if status == "active":
            query = query.filter(isActive=True)
        elif status == "inactive":
            query = query.filter(isActive=False)
        
        # Фильтр по родителю
        if parent_id:
            query = query.filter(id_user=parent_id)
        
        # Поиск по названию
        if search:
            query = query.filter(title__icontains=search)
        
        # Подсчет общего количества
        total = await query.count()
        
        # Пагинация
        offset = (page - 1) * per_page
        schedules = await query.offset(offset).limit(per_page).all()
        
        # Формируем результат
        result = []
        for schedule in schedules:
            # Получаем информацию о родителе
            parent = await UsersUser.filter(id=schedule.id_user).first()
            
            # Получаем маршруты
            roads = await DataScheduleRoad.filter(
                id_schedule=schedule.id,
                isActive=True
            ).count()
            
            # Получаем назначенных водителей
            from models.orders_db import DataScheduleRoadDriver
            road_ids = await DataScheduleRoad.filter(
                id_schedule=schedule.id,
                isActive=True
            ).values_list("id", flat=True)
            
            drivers_count = 0
            if road_ids:
                drivers_count = await DataScheduleRoadDriver.filter(
                    id_schedule_road__in=road_ids,
                    isActive=True
                ).count()
            
            result.append({
                "id": schedule.id,
                "title": schedule.title,
                "description": schedule.description,
                "children_count": schedule.children_count,
                "duration": schedule.duration,
                "week_days": schedule.week_days,
                "is_active": schedule.isActive,
                "datetime_create": schedule.datetime_create.isoformat() if schedule.datetime_create else None,
                "parent": {
                    "id": parent.id if parent else None,
                    "name": parent.name if parent else None,
                    "surname": parent.surname if parent else None,
                    "phone": parent.phone if parent else None
                },
                "roads_count": roads,
                "drivers_assigned": drivers_count
            })
        
        logger.info(
            f"Admin {request.user} viewed schedules list",
            extra={
                "admin_id": request.user,
                "page": page,
                "per_page": per_page,
                "total": total,
                "filters": {
                    "status": status,
                    "parent_id": parent_id,
                    "search": search
                },
                "event_type": "admin_schedules_list_viewed"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Success",
            "data": result,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logger.error(
            f"Error getting schedules list: {str(e)}",
            extra={
                "admin_id": request.user,
                "error": str(e),
                "event_type": "admin_schedules_list_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при получении списка контрактов"
        }, 500)


@router.get("/schedules/{schedule_id}")
async def get_schedule_details(request: Request, schedule_id: int):
    """
    BE-MVP-024: Получение детальной информации о контракте для админа.
    
    Админ может просмотреть полную информацию о контракте:
    время, адреса, назначенных водителей, детей.
    
    Args:
        request: Объект запроса
        schedule_id: ID контракта
        
    Returns:
        JSONResponse: Детальная информация о контракте
    """
    try:
        # Получаем контракт
        schedule = await DataSchedule.filter(id=schedule_id).first()
        
        if not schedule:
            return JSONResponse({
                "status": False,
                "message": "Контракт не найден"
            }, 404)
        
        # Получаем родителя
        parent = await UsersUser.filter(id=schedule.id_user).first()
        
        # Получаем маршруты
        roads = await DataScheduleRoad.filter(
            id_schedule=schedule_id,
            isActive=True
        ).all()
        
        roads_data = []
        for road in roads:
            # Получаем адреса
            addresses = await DataScheduleRoadAddress.filter(
                id_schedule_road=road.id,
                isActive=True
            ).all()
            
            addresses_data = []
            for addr in addresses:
                addresses_data.append({
                    "id": addr.id,
                    "from_address": addr.from_address,
                    "to_address": addr.to_address,
                    "from_latitude": float(addr.from_latitude) if addr.from_latitude else None,
                    "from_longitude": float(addr.from_longitude) if addr.from_longitude else None,
                    "to_latitude": float(addr.to_latitude) if addr.to_latitude else None,
                    "to_longitude": float(addr.to_longitude) if addr.to_longitude else None
                })
            
            # Получаем детей
            children_ids = await DataScheduleRoadChild.filter(
                id_schedule_road=road.id,
                isActive=True
            ).values_list("id_child", flat=True)
            
            children_data = []
            for child_id in children_ids:
                child = await UsersChild.filter(id=child_id).first()
                if child:
                    children_data.append({
                        "id": child.id,
                        "name": child.name,
                        "surname": child.surname,
                        "age": child.age
                    })
            
            # Получаем контакт
            contact = await DataScheduleRoadContact.filter(
                id_schedule_road=road.id,
                isActive=True
            ).first()
            
            # Получаем назначенного водителя
            from models.orders_db import DataScheduleRoadDriver
            driver_assignment = await DataScheduleRoadDriver.filter(
                id_schedule_road=road.id,
                isActive=True
            ).first()
            
            driver_data = None
            if driver_assignment:
                driver = await UsersUser.filter(id=driver_assignment.id_driver).first()
                if driver:
                    driver_data = {
                        "id": driver.id,
                        "name": driver.name,
                        "surname": driver.surname,
                        "phone": driver.phone
                    }
            
            roads_data.append({
                "id": road.id,
                "title": road.title,
                "week_day": road.week_day,
                "start_time": road.start_time,
                "end_time": road.end_time,
                "type_drive": road.type_drive,
                "amount": float(road.amount) if road.amount else None,
                "addresses": addresses_data,
                "children": children_data,
                "contact": {
                    "name": contact.name if contact else None,
                    "phone": contact.phone if contact else None
                } if contact else None,
                "driver": driver_data
            })
        
        logger.info(
            f"Admin {request.user} viewed schedule {schedule_id} details",
            extra={
                "admin_id": request.user,
                "schedule_id": schedule_id,
                "parent_id": schedule.id_user,
                "event_type": "admin_schedule_details_viewed"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Success",
            "schedule": {
                "id": schedule.id,
                "title": schedule.title,
                "description": schedule.description,
                "children_count": schedule.children_count,
                "duration": schedule.duration,
                "week_days": schedule.week_days,
                "is_active": schedule.isActive,
                "datetime_create": schedule.datetime_create.isoformat() if schedule.datetime_create else None,
                "parent": {
                    "id": parent.id if parent else None,
                    "name": parent.name if parent else None,
                    "surname": parent.surname if parent else None,
                    "phone": parent.phone if parent else None
                },
                "roads": roads_data
            }
        })
        
    except Exception as e:
        logger.error(
            f"Error getting schedule details: {str(e)}",
            extra={
                "admin_id": request.user,
                "schedule_id": schedule_id,
                "error": str(e),
                "event_type": "admin_schedule_details_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при получении деталей контракта"
        }, 500)


# ============================================================================
# BE-MVP-025: Телефон водителя в профиле (админка)
# ============================================================================

@router.get("/drivers/{driver_id}")
async def get_driver_profile(request: Request, driver_id: int):
    """
    BE-MVP-025: Получение профиля водителя для админа.
    
    Админ может просмотреть профиль водителя с телефоном под датой регистрации.
    
    Args:
        request: Объект запроса
        driver_id: ID водителя
        
    Returns:
        JSONResponse: Профиль водителя
    """
    try:
        # Получаем водителя
        driver = await UsersUser.filter(id=driver_id).first()
        
        if not driver:
            return JSONResponse({
                "status": False,
                "message": "Водитель не найден"
            }, 404)
        
        # Получаем данные водителя
        driver_data = await UsersDriverData.filter(id_driver=driver_id).first()
        
        # Получаем фото
        photo = await UsersUserPhoto.filter(id_user=driver_id).first()
        
        # Получаем верификацию
        verification = await UsersVerifyAccount.filter(id_user=driver_id).first()
        
        # Получаем статистику заказов
        from models.orders_db import DataScheduleRoadDriver
        total_orders = await DataScheduleRoadDriver.filter(
            id_driver=driver_id,
            isActive=True
        ).count()
        
        logger.info(
            f"Admin {request.user} viewed driver {driver_id} profile",
            extra={
                "admin_id": request.user,
                "driver_id": driver_id,
                "event_type": "admin_driver_profile_viewed"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Success",
            "driver": {
                "id": driver.id,
                "name": driver.name,
                "surname": driver.surname,
                "phone": driver.phone,  # BE-MVP-025: Телефон для копирования
                "datetime_create": driver.datetime_create.isoformat() if driver.datetime_create else None,
                "is_active": driver.isActive,
                "photo_path": photo.photo_path if photo else None,
                "driver_data": {
                    "license_number": driver_data.license_number if driver_data else None,
                    "car_model": driver_data.car_model if driver_data else None,
                    "car_number": driver_data.car_number if driver_data else None,
                    "car_color": driver_data.car_color if driver_data else None,
                    "is_active": driver_data.isActive if driver_data else None
                } if driver_data else None,
                "verification": {
                    "is_verified": verification.is_verified if verification else False,
                    "verification_date": verification.verification_date.isoformat() if verification and verification.verification_date else None
                } if verification else None,
                "statistics": {
                    "total_orders": total_orders
                }
            }
        })
        
    except Exception as e:
        logger.error(
            f"Error getting driver profile: {str(e)}",
            extra={
                "admin_id": request.user,
                "driver_id": driver_id,
                "error": str(e),
                "event_type": "admin_driver_profile_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при получении профиля водителя"
        }, 500)


# ============================================================================
# BE-MVP-028: API истории транзакций
# ============================================================================

@router.get("/transactions")
async def get_all_transactions(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    user_id: int = None,
    start_date: str = None,
    end_date: str = None,
    transaction_type: str = None
):
    """
    BE-MVP-028: Получение истории всех транзакций для админа.
    
    Админ может просмотреть историю платежей всех пользователей с фильтрацией.
    
    Args:
        request: Объект запроса
        page: Номер страницы
        per_page: Количество на странице
        user_id: Фильтр по пользователю
        start_date: Начальная дата (YYYY-MM-DD)
        end_date: Конечная дата (YYYY-MM-DD)
        transaction_type: Тип транзакции
        
    Returns:
        JSONResponse: История транзакций
    """
    try:
        # Строим запрос
        query = HistoryPaymentTink.filter()
        
        # Фильтры
        if user_id:
            query = query.filter(id_user=user_id)
        
        if start_date:
            from datetime import datetime
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(datetime_create__gte=start_dt)
        
        if end_date:
            from datetime import datetime
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(datetime_create__lte=end_dt)
        
        if transaction_type:
            if transaction_type == "deposit":
                query = query.filter(amount__gt=0)
            elif transaction_type == "withdrawal":
                query = query.filter(amount__lt=0)
        
        # Подсчет
        total = await query.count()
        
        # Пагинация
        offset = (page - 1) * per_page
        transactions = await query.order_by("-datetime_create").offset(offset).limit(per_page).all()
        
        # Формируем результат
        result = []
        for transaction in transactions:
            user = await UsersUser.filter(id=transaction.id_user).first()
            result.append({
                "id": transaction.id,
                "amount": float(transaction.amount),
                "datetime_create": transaction.datetime_create.isoformat() if transaction.datetime_create else None,
                "status": transaction.status if hasattr(transaction, 'status') else "completed",
                "description": transaction.description if hasattr(transaction, 'description') else None,
                "payment_id": transaction.payment_id if hasattr(transaction, 'payment_id') else None,
                "user": {
                    "id": user.id if user else None,
                    "name": user.name if user else None,
                    "surname": user.surname if user else None,
                    "phone": user.phone if user else None
                }
            })
        
        # Статистика
        total_amount = sum(float(t.amount) for t in transactions)
        
        logger.info(
            f"Admin {request.user} viewed all transactions",
            extra={
                "admin_id": request.user,
                "page": page,
                "total": total,
                "filters": {
                    "user_id": user_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "transaction_type": transaction_type
                },
                "event_type": "admin_transactions_viewed"
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
            f"Error getting all transactions: {str(e)}",
            extra={
                "admin_id": request.user,
                "error": str(e),
                "event_type": "admin_transactions_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при получении истории транзакций"
        }, 500)


# ============================================================================
# BE-MVP-029: API настройки коэффициентов формул
# ============================================================================

@router.get("/pricing_coefficients")
async def get_pricing_coefficients(request: Request):
    """
    BE-MVP-029: Получение текущих коэффициентов формул расчета стоимости.
    
    Админ может просмотреть текущие значения всех коэффициентов.
    
    Returns:
        JSONResponse: Текущие коэффициенты
    """
    try:
        # Получаем активные коэффициенты
        coefficients = await PricingCoefficients.filter(is_active=True).first()
        
        if not coefficients:
            # Создаем дефолтные коэффициенты если их нет
            from datetime import datetime
            coefficients = await PricingCoefficients.create(
                vm=27,
                s1=3,
                kc=3,
                ks=1,
                kg=1,
                is_active=True,
                datetime_create=datetime.now()
            )
        
        logger.info(
            f"Admin {request.user} viewed pricing coefficients",
            extra={
                "admin_id": request.user,
                "coefficients_id": coefficients.id,
                "event_type": "admin_pricing_coefficients_viewed"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Success",
            "coefficients": {
                "id": coefficients.id,
                "vm": float(coefficients.vm),
                "s1": float(coefficients.s1),
                "kc": float(coefficients.kc),
                "ks": float(coefficients.ks),
                "kg": float(coefficients.kg),
                "t1": float(coefficients.t1),
                "m": float(coefficients.m),
                "x5": float(coefficients.x5),
                "p_insurance": float(coefficients.p_insurance),
                "datetime_update": coefficients.datetime_update.isoformat() if coefficients.datetime_update else None,
                "updated_by": coefficients.updated_by
            },
            "descriptions": {
                "vm": "Средняя скорость движения автомобиля (км/ч)",
                "s1": "Радиус подачи автомобиля (км)",
                "kc": "Коэффициент кэшбека (%)",
                "ks": "Коэффициент страховки (%) - устаревший",
                "kg": "Городской коэффициент (%)",
                "t1": "Время за 1 км пути (мин)",
                "m": "Стоимость 1 км пути (руб)",
                "x5": "Процент на маркетинг (%)",
                "p_insurance": "Страховка (руб)"
            }
        })
        
    except Exception as e:
        logger.error(
            f"Error getting pricing coefficients: {str(e)}",
            extra={
                "admin_id": request.user,
                "error": str(e),
                "event_type": "admin_pricing_coefficients_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при получении коэффициентов"
        }, 500)


@router.put("/pricing_coefficients")
async def update_pricing_coefficients(
    request: Request,
    vm: float = None,
    s1: float = None,
    kc: float = None,
    ks: float = None,
    kg: float = None,
    t1: float = None,
    m: float = None,
    x5: float = None,
    p_insurance: float = None
):
    """
    BE-MVP-029: Обновление коэффициентов формул расчета стоимости.
    
    Админ может обновить значения коэффициентов.
    Только для администраторов.
    Соответствует ТЗ раздел 4.4.
    
    Args:
        request: Объект запроса
        vm: Средняя скорость движения (км/ч)
        s1: Радиус подачи автомобиля (км)
        kc: Коэффициент кэшбека (%)
        ks: Коэффициент страховки (%) - устаревший
        kg: Городской коэффициент (%)
        t1: Время за 1 км пути (мин)
        m: Стоимость 1 км пути (руб)
        x5: Процент на маркетинг (%)
        p_insurance: Страховка (руб)
        
    Returns:
        JSONResponse: Обновленные коэффициенты
    """
    try:
        # Получаем текущие коэффициенты
        coefficients = await PricingCoefficients.filter(is_active=True).first()
        
        if not coefficients:
            # Создаем если их нет
            from datetime import datetime
            coefficients = await PricingCoefficients.create(
                vm=27,
                s1=3,
                kc=3,
                ks=1,
                kg=1,
                is_active=True,
                datetime_create=datetime.now()
            )
        
        # Сохраняем старые значения для логирования
        old_values = {
            "vm": float(coefficients.vm),
            "s1": float(coefficients.s1),
            "kc": float(coefficients.kc),
            "ks": float(coefficients.ks),
            "kg": float(coefficients.kg),
            "t1": float(coefficients.t1),
            "m": float(coefficients.m),
            "x5": float(coefficients.x5),
            "p_insurance": float(coefficients.p_insurance)
        }
        
        # Обновляем только те значения, которые переданы
        updates = {}
        if vm is not None:
            updates["vm"] = vm
        if s1 is not None:
            updates["s1"] = s1
        if kc is not None:
            updates["kc"] = kc
        if ks is not None:
            updates["ks"] = ks
        if kg is not None:
            updates["kg"] = kg
        if t1 is not None:
            updates["t1"] = t1
        if m is not None:
            updates["m"] = m
        if x5 is not None:
            updates["x5"] = x5
        if p_insurance is not None:
            updates["p_insurance"] = p_insurance
        
        if not updates:
            return JSONResponse({
                "status": False,
                "message": "Не указаны параметры для обновления"
            }, 400)
        
        # Добавляем служебные поля
        from datetime import datetime
        updates["datetime_update"] = datetime.now()
        updates["updated_by"] = request.user
        
        # Обновляем
        await PricingCoefficients.filter(id=coefficients.id).update(**updates)
        
        # Получаем обновленные значения
        updated_coefficients = await PricingCoefficients.filter(id=coefficients.id).first()
        
        new_values = {
            "vm": float(updated_coefficients.vm),
            "s1": float(updated_coefficients.s1),
            "kc": float(updated_coefficients.kc),
            "ks": float(updated_coefficients.ks),
            "kg": float(updated_coefficients.kg),
            "t1": float(updated_coefficients.t1),
            "m": float(updated_coefficients.m),
            "x5": float(updated_coefficients.x5),
            "p_insurance": float(updated_coefficients.p_insurance)
        }
        
        # Логируем изменения
        logger.info(
            f"Admin {request.user} updated pricing coefficients",
            extra={
                "admin_id": request.user,
                "coefficients_id": coefficients.id,
                "old_values": old_values,
                "new_values": new_values,
                "changed_fields": list(updates.keys()),
                "event_type": "admin_pricing_coefficients_updated"
            }
        )
        
        return JSONResponse({
            "status": True,
            "message": "Коэффициенты успешно обновлены",
            "coefficients": {
                "id": updated_coefficients.id,
                "vm": float(updated_coefficients.vm),
                "s1": float(updated_coefficients.s1),
                "kc": float(updated_coefficients.kc),
                "ks": float(updated_coefficients.ks),
                "kg": float(updated_coefficients.kg),
                "t1": float(updated_coefficients.t1),
                "m": float(updated_coefficients.m),
                "x5": float(updated_coefficients.x5),
                "p_insurance": float(updated_coefficients.p_insurance),
                "datetime_update": updated_coefficients.datetime_update.isoformat(),
                "updated_by": updated_coefficients.updated_by
            }
        })
        
    except Exception as e:
        logger.error(
            f"Error updating pricing coefficients: {str(e)}",
            extra={
                "admin_id": request.user,
                "error": str(e),
                "event_type": "admin_pricing_coefficients_update_error"
            }
        )
        return JSONResponse({
            "status": False,
            "message": "Ошибка при обновлении коэффициентов"
        }, 500)

