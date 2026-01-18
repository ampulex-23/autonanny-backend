"""
Вспомогательные функции для работы с API ответами.
BE-MVP-003: Рефакторинг orders.py
"""
import json
from models.orders_db import DataScheduleRoadChild, DataScheduleRoadContact


def generate_responses(answers: list) -> dict:
    """
    Генерирует словарь ответов для OpenAPI документации FastAPI.
    
    Args:
        answers: Список JSONResponse объектов с примерами ответов
        
    Returns:
        dict: Словарь с описаниями ответов для каждого статус-кода
        
    Example:
        >>> responses = generate_responses([success_answer, error_response])
        >>> @router.get("/endpoint", responses=responses)
    """
    answer = {}
    for data in answers:
        description = json.loads(data.body.decode('utf-8'))
        if "message" in description:
            description = description["message"]
        elif "detail" in description:
            description = description["detail"]
        else:
            description = "Response"
        answer[data.status_code] = {
            "content": {
                "application/json": {
                    "example": json.loads(data.body.decode("utf-8"))
                }
            },
            "description": description
        }
    return answer


async def enrich_roads_with_children_and_contact(roads: list) -> list:
    """
    Обогащает список маршрутов информацией о детях и контактных лицах.
    
    Args:
        roads: Список маршрутов (dict) с полем "id"
        
    Returns:
        list: Тот же список маршрутов с добавленными полями:
            - children: list[int] - ID детей
            - contact: dict | None - Контактное лицо
            
    Example:
        >>> roads = await DataScheduleRoad.filter(...).values()
        >>> enriched = await enrich_roads_with_children_and_contact(roads)
    """
    for road in roads:
        # Получаем детей для маршрута
        children_records = await DataScheduleRoadChild.filter(
            id_schedule_road=road["id"], 
            isActive=True
        ).all().values("id_child")
        road["children"] = [rec["id_child"] for rec in children_records]

        # Получаем контактное лицо для маршрута
        contact_exists = await DataScheduleRoadContact.filter(
            id_schedule_road=road["id"], 
            isActive=True
        ).count() > 0
        
        if contact_exists:
            contact_record = await DataScheduleRoadContact.filter(
                id_schedule_road=road["id"], 
                isActive=True
            ).first().values("surname", "name", "patronymic", "contact_phone")
            
            road["contact"] = {
                "surname": contact_record["surname"],
                "name": contact_record["name"],
                "patronymic": contact_record["patronymic"],
                "phone": contact_record["contact_phone"]
            }
        else:
            road["contact"] = None
            
    return roads
