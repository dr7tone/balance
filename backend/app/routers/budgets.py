"""Бюджет на месяц: лимиты по категориям и контроль исполнения."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..deps import get_current_user
from ..schemas import BudgetCopy, BudgetInput, BudgetStatusOut

router = APIRouter(prefix="/budgets", tags=["budgets"])


def _month_range(month: str) -> tuple[date, date]:
    year, mon = int(month[:4]), int(month[5:7])
    start = date(year, mon, 1)
    end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)
    return start, end


def _spent_for_category(db: Session, user_id: int, category_id: int,
                        month: str) -> float:
    """Сумма расходов по категории за месяц (работает в SQLite и PostgreSQL)."""
    start, end = _month_range(month)
    total = (db.query(func.coalesce(func.sum(models.Operation.amount), 0))
             .filter(models.Operation.user_id == user_id,
                     models.Operation.type == "expense",
                     models.Operation.category_id == category_id,
                     models.Operation.date >= start,
                     models.Operation.date < end)
             .scalar())
    return float(total or 0)


@router.get("/status", response_model=list[BudgetStatusOut])
def budget_status(month: str = Query(pattern=r"^\d{4}-\d{2}$"),
                  user: models.User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    budgets = (db.query(models.Budget)
               .filter(models.Budget.user_id == user.id,
                       models.Budget.month == month)
               .all())
    out = []
    for b in budgets:
        cat = db.get(models.Category, b.category_id)
        spent = _spent_for_category(db, user.id, b.category_id, month)
        percent = round(spent / float(b.limit_amount) * 100, 1) if float(b.limit_amount) else 0
        out.append(BudgetStatusOut(
            budget_id=b.id,
            category_id=b.category_id,
            category_name=cat.name if cat else "—",
            month=b.month,
            limit_amount=float(b.limit_amount),
            spent=spent,
            remaining=round(float(b.limit_amount) - spent, 2),
            percent=percent,
        ))
    return out


@router.post("")
def upsert_budget(data: BudgetInput,
                  user: models.User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    cat = db.get(models.Category, data.category_id)
    if cat is None or cat.user_id != user.id:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    if cat.type != "expense":
        raise HTTPException(status_code=400, detail="Лимит можно задавать только для расходов")
    budget = (db.query(models.Budget)
              .filter(models.Budget.user_id == user.id,
                      models.Budget.category_id == data.category_id,
                      models.Budget.month == data.month)
              .first())
    if budget is None:
        budget = models.Budget(user_id=user.id, category_id=data.category_id,
                               month=data.month, limit_amount=data.limit_amount)
        db.add(budget)
    else:
        budget.limit_amount = data.limit_amount
    db.commit()
    return {"ok": True, "category_id": data.category_id,
            "month": data.month, "limit_amount": data.limit_amount}


@router.post("/copy")
def copy_budgets(data: BudgetCopy,
                 user: models.User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """Скопировать все лимиты с одного месяца на другой."""
    if data.from_month == data.to_month:
        raise HTTPException(status_code=400, detail="Месяцы должны отличаться")
    source = (db.query(models.Budget)
              .filter(models.Budget.user_id == user.id,
                      models.Budget.month == data.from_month)
              .all())
    copied = 0
    for b in source:
        cat = db.get(models.Category, b.category_id)
        if cat is None or cat.user_id != user.id:
            continue
        target = (db.query(models.Budget)
                  .filter(models.Budget.user_id == user.id,
                          models.Budget.category_id == b.category_id,
                          models.Budget.month == data.to_month)
                  .first())
        if target is None:
            db.add(models.Budget(user_id=user.id, category_id=b.category_id,
                                 month=data.to_month, limit_amount=b.limit_amount))
            copied += 1
    db.commit()
    return {"copied": copied, "from_month": data.from_month, "to_month": data.to_month}


@router.delete("/{budget_id}", status_code=204)
def delete_budget(budget_id: int,
                  user: models.User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    budget = db.get(models.Budget, budget_id)
    if budget is None or budget.user_id != user.id:
        raise HTTPException(status_code=404, detail="Бюджет не найден")
    db.delete(budget)
    db.commit()
