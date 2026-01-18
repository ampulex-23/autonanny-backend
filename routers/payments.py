import datetime
import decimal
import json
from fastapi.responses import RedirectResponse, JSONResponse
import requests
from fastapi import APIRouter, HTTPException, Request, Body

from config import settings
from const.admins_const import success_answer
from defs import generate_fb_link, logger
from models.users_db import HistoryPaymentTink, DataUserBalance, DataUserBalanceHistory
from utils.response_helpers import generate_responses

router = APIRouter()

@router.get("/payments_success",
            responses=generate_responses([]))
async def payments_success(order_id: str):
    terminal_key = settings.tinkoff_terminal_key
    content_type = {"Content-Type": "application/json"}
    if await HistoryPaymentTink.filter(id_order=order_id, datetime_create=datetime.datetime.now().date()).count() == 0:
        return RedirectResponse("https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=youtu.be", 307)

    pay = await HistoryPaymentTink.filter(id_order=order_id,
                                          datetime_create=datetime.datetime.now().date()).first().values()
    data = {
            "TerminalKey": terminal_key,
            "PaymentId": pay["id_payment"],
            "Token": pay["token"],
    }
    x = requests.post("https://securepay.tinkoff.ru/v2/GetState", json=data, headers=content_type).json()
    print(x)
    if x["Status"] not in ["CONFIRMING", "CONFIRMED"]:
        return RedirectResponse("https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=youtu.be", 307)
    user =  await DataUserBalance.filter(id_user=pay["id_user"]).first().values()
    if user is None:
        await DataUserBalance.create(id_user=pay["id_user"], money=pay["amount"])
    user =  await DataUserBalance.filter(id_user=pay["id_user"]).first().values()
    await DataUserBalance.filter(id_user=pay["id_user"]).update(money=user["money"]+decimal.Decimal(pay["amount"]))
    await DataUserBalanceHistory.create(id_user=pay["id_user"], money=decimal.Decimal(pay["amount"]), id_task=-1,
                                    isComplete=True, description="Пополнение баланса пользователя с банковской карты")
    return RedirectResponse(await generate_fb_link(), 307)

@router.get("/payments_unsuccessful",
            responses=generate_responses([]))
async def payments_success(order_id: str):
    return RedirectResponse("https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=youtu.be", 307)

@router.post("/payments_status/{order_id}")
async def get_status_payment(request: Request, order_id: str):
    """
    Webhook для получения уведомлений о статусе платежа от Tinkoff.
    
    Args:
        request: HTTP запрос от Tinkoff
        order_id: ID заказа
        
    Returns:
        JSONResponse: Подтверждение получения уведомления
    """
    try:
        # Получаем данные от Tinkoff
        body = await request.body()
        payment_data = await request.json()
        
        logger.info(f"Payment status webhook received for order {order_id}", 
                   extra={"order_id": order_id, "payment_data": payment_data})
        
        # Проверяем наличие платежа в БД
        payment = await HistoryPaymentTink.filter(id_order=order_id).first()
        if not payment:
            logger.warning(f"Payment not found for order {order_id}")
            return JSONResponse({"status": "ERROR", "message": "Payment not found"}, 404)
        
        # Обрабатываем статус платежа
        status = payment_data.get("Status")
        payment_id = payment_data.get("PaymentId")
        amount = payment_data.get("Amount", 0) / 100  # Конвертируем из копеек в рубли
        
        if status in ["CONFIRMED", "CONFIRMING"]:
            # Начисляем средства на баланс
            user_balance = await DataUserBalance.filter(id_user=payment.id_user).first()
            if not user_balance:
                await DataUserBalance.create(id_user=payment.id_user, amount=amount)
            else:
                await DataUserBalance.filter(id_user=payment.id_user).update(
                    amount=user_balance.amount + decimal.Decimal(amount)
                )
            
            # Создаем запись в истории
            await DataUserBalanceHistory.create(
                id_user=payment.id_user,
                money=decimal.Decimal(amount),
                id_task=-1,
                isComplete=True,
                description=f"Пополнение баланса через Tinkoff (PaymentId: {payment_id})"
            )
            
            logger.info(f"Balance updated for user {payment.id_user}, amount: {amount}",
                       extra={"user_id": payment.id_user, "amount": amount, "payment_id": payment_id})
        
        elif status in ["REJECTED", "CANCELED"]:
            logger.warning(f"Payment {payment_id} was {status}",
                          extra={"payment_id": payment_id, "status": status})
        
        return JSONResponse({"status": "OK"}, 200)
        
    except Exception as e:
        logger.error(f"Error processing payment webhook: {str(e)}",
                    extra={"order_id": order_id, "error": str(e)})
        return JSONResponse({"status": "ERROR", "message": str(e)}, 500)

