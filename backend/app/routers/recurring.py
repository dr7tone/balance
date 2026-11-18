"""Регулярные платежи: подписки, аренда, зарплата и другие повторяющиеся операции."""
import calendar
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..deps import get_current_user
from ..schemas import RecurringCreate, RecurringOut, RecurringPayOut, RecurringUpdate

router = APIRouter(prefix="/recurring", tags=["recurring"])


def _add_month(value: date, months: int = 1) -> date:
    year = value.year + (value.month - 1 + months) // 12
    month = (value.month - 1 + months) % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _to_out(item: models.RecurringPayment) -> RecurringOut:
    return RecurringOut(
        id=item.id,
        name=item.name,
        type=item.type,
        amount=float(item.amount),
        category_id=item.category_id,
        category_name=item.category.name if item.category else None,
        next_date=item.next_date,
        period=item.period,
        is_active=item.is_active,
        created_at=item.created_at,
    )


def _check_category(db: Session, user_id: int, category_id: int | None,
                    op_type: str) -> None:
    if category_id is None:
        return
    cat = db.get(models.Category, category_id)
    if cat is None or cat.user_id != user_id:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    if cat.type != op_type:
        raise HTTPException(status_code=400,
                            detail="Тип категории не совпадает с типом платежа")


def _get_item(db: Session, user_id: int, item_id: int) -> models.RecurringPayment:
    item = db.get(models.RecurringPayment, item_id)
    if item is None or item.user_id != user_id:
        raise HTTPException(status_code=404, detail="Регулярный платёж не найден")
    return item


@router.get("", response_model=list[RecurringOut])
def list_recurring(user: models.User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    items = (db.query(models.RecurringPayment)
             .filter(models.RecurringPayment.user_id == user.id)
             .order_by(models.RecurringPayment.next_date,
                       models.RecurringPayment.id)
             .all())
    return [_to_out(i) for i in items]


@router.post("", response_model=RecurringOut)
def create_recurring(data: RecurringCreate,
                     user: models.User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    _check_category(db, user.id, data.category_id, data.type)
    item = models.RecurringPayment(user_id=user.id, name=data.name,
                                   type=data.type, amount=data.amount,
                                   category_id=data.category_id,
                                   next_date=data.next_date,
                                   period=data.period,
                                   is_active=data.is_active)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item)


@router.patch("/{item_id}", response_model=RecurringOut)
def update_recurring(item_id: int, data: RecurringUpdate,
                     user: models.User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    item = _get_item(db, user.id, item_id)
    new_type = data.type if data.type is not None else item.type
    if "category_id" in data.model_fields_set:
        _check_category(db, user.id, data.category_id, new_type)
        item.category_id = data.category_id
    if data.name is not None:
        item.name = data.name
    if data.type is not None:
        item.type = data.type
    if data.amount is not None:
        item.amount = data.amount
    if data.next_date is not None:
        item.next_date = data.next_date
    if data.period is not None:
        item.period = data.period
    if data.is_active is not None:
        item.is_active = data.is_active
    db.commit()
    db.refresh(item)
    return _to_out(item)


@router.delete("/{item_id}", status_code=204)
def delete_recurring(item_id: int,
                     user: models.User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    item = _get_item(db, user.id, item_id)
    db.delete(item)
    db.commit()


def _pay_item(db: Session, user: models.User,
              item: models.RecurringPayment) -> int:
    operation = models.Operation(user_id=user.id,
                                 type=item.type,
                                 amount=item.amount,
                                 date=item.next_date,
                                 category_id=item.category_id,
                                 comment=f"Регулярный платёж: {item.name}")
    db.add(operation)
    item.next_date = _add_month(item.next_date)
    db.flush()
    return operation.id


@router.post("/{item_id}/pay", response_model=RecurringPayOut)
def pay_recurring(item_id: int,
                  user: models.User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    item = _get_item(db, user.id, item_id)
    if not item.is_active:
        raise HTTPException(status_code=400, detail="Регулярный платёж отключён")
    operation_id = _pay_item(db, user, item)
    db.commit()
    db.refresh(item)
    return RecurringPayOut(recurring=_to_out(item), operation_id=operation_id)


@router.post("/process-due")
def process_due(user: models.User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    today = date.today()
    items = (db.query(models.RecurringPayment)
             .filter(models.RecurringPayment.user_id == user.id,
                     models.RecurringPayment.is_active.is_(True),
                     models.RecurringPayment.next_date <= today)
             .all())
    operation_ids = [_pay_item(db, user, item) for item in items]
    db.commit()
    return {"paid": len(operation_ids), "operation_ids": operation_ids}
