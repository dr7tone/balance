"""Анализ доходов и расходов: сводка, динамика, структура, прогноз."""
import calendar
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..deps import get_current_user
from ..schemas import CategoryAgg, DailyPoint, ForecastOut, MonthlyPoint, SummaryOut

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _sum_by_type(db: Session, user_id: int, op_type: str,
                 date_from: date | None, date_to: date | None) -> float:
    q = db.query(func.coalesce(func.sum(models.Operation.amount), 0)).filter(
        models.Operation.user_id == user_id,
        models.Operation.type == op_type)
    if date_from:
        q = q.filter(models.Operation.date >= date_from)
    if date_to:
        q = q.filter(models.Operation.date <= date_to)
    return float(q.scalar() or 0)


@router.get("/summary", response_model=SummaryOut)
def summary(user: models.User = Depends(get_current_user),
            db: Session = Depends(get_db),
            date_from: date | None = None,
            date_to: date | None = None):
    income = _sum_by_type(db, user.id, "income", date_from, date_to)
    expense = _sum_by_type(db, user.id, "expense", date_from, date_to)

    q_count = db.query(func.count(models.Operation.id)).filter(
        models.Operation.user_id == user.id)
    if date_from:
        q_count = q_count.filter(models.Operation.date >= date_from)
    if date_to:
        q_count = q_count.filter(models.Operation.date <= date_to)
    count = q_count.scalar() or 0

    rows = (db.query(
                models.Category.name,
                func.coalesce(func.sum(models.Operation.amount), 0))
            .join(models.Operation, models.Operation.category_id == models.Category.id)
            .filter(models.Operation.user_id == user.id,
                    models.Operation.type == "expense")
            .group_by(models.Category.name)
            .order_by(func.sum(models.Operation.amount).desc())
            .limit(5)
            .all())
    top = []
    for name, amount in rows:
        amt = float(amount)
        top.append(CategoryAgg(category_id=None, category_name=name,
                               amount=amt,
                               percent=round(amt / expense * 100, 1) if expense else 0))
    return SummaryOut(income=round(income, 2), expense=round(expense, 2),
                      balance=round(income - expense, 2),
                      operations_count=count, top_categories=top)


@router.get("/monthly", response_model=list[MonthlyPoint])
def monthly(months: int = Query(default=6, ge=1, le=24),
            user: models.User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    today = date.today()
    cur = date(today.year, today.month, 1)
    points: list[MonthlyPoint] = []
    for _ in range(months):
        key = f"{cur.year:04d}-{cur.month:02d}"
        nxt = (date(cur.year + 1, 1, 1) if cur.month == 12
               else date(cur.year, cur.month + 1, 1))
        inc = _sum_by_type(db, user.id, "income", cur, nxt - timedelta(days=1))
        exp = _sum_by_type(db, user.id, "expense", cur, nxt - timedelta(days=1))
        points.append(MonthlyPoint(month=key, income=round(inc, 2),
                                   expense=round(exp, 2),
                                   balance=round(inc - exp, 2)))
        cur = (date(cur.year - 1, 12, 1) if cur.month == 1
               else date(cur.year, cur.month - 1, 1))
    points.reverse()
    return points


@router.get("/daily", response_model=list[DailyPoint])
def daily(month: str = Query(pattern=r"^\d{4}-\d{2}$", default=""),
          user: models.User = Depends(get_current_user),
          db: Session = Depends(get_db)):
    """Доходы и расходы по дням выбранного месяца (для графика и календаря)."""
    today = date.today()
    if not month:
        month = f"{today.year:04d}-{today.month:02d}"
    year, mon = int(month[:4]), int(month[5:7])
    days = calendar.monthrange(year, mon)[1]
    start = date(year, mon, 1)
    end = date(year, mon, days)
    rows = (db.query(models.Operation.date,
                     models.Operation.type,
                     func.coalesce(func.sum(models.Operation.amount), 0))
            .filter(models.Operation.user_id == user.id,
                    models.Operation.date >= start,
                    models.Operation.date <= end)
            .group_by(models.Operation.date, models.Operation.type)
            .all())
    facts: dict[tuple[date, str], float] = {}
    for d, t, amount in rows:
        facts[(d, t)] = float(amount)
    return [
        DailyPoint(
            date=date(year, mon, day),
            income=round(facts.get((date(year, mon, day), "income"), 0), 2),
            expense=round(facts.get((date(year, mon, day), "expense"), 0), 2),
        )
        for day in range(1, days + 1)
    ]


@router.get("/forecast", response_model=ForecastOut)
def forecast(month: str = Query(pattern=r"^\d{4}-\d{2}$", default=""),
             user: models.User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    """Прогноз расходов до конца месяца и дневной безопасный лимит."""
    today = date.today()
    if not month:
        month = f"{today.year:04d}-{today.month:02d}"
    year, mon = int(month[:4]), int(month[5:7])
    days = calendar.monthrange(year, mon)[1]
    start = date(year, mon, 1)
    end = date(year, mon, days)

    income = _sum_by_type(db, user.id, "income", start, end)
    expense = _sum_by_type(db, user.id, "expense", start, end)

    is_current = (year, mon) == (today.year, today.month)
    days_passed = today.day if is_current else (
        days if (year, mon) < (today.year, today.month) else 0)
    days_passed = max(days_passed, 1)
    days_left = max(days - days_passed, 0) if is_current else 0
    daily_average = expense / days_passed
    projected = expense if not is_current else expense + daily_average * days_left

    total_budget = float(
        db.query(func.coalesce(func.sum(models.Budget.limit_amount), 0))
        .filter(models.Budget.user_id == user.id,
                models.Budget.month == month)
        .scalar() or 0
    )
    budget_left = max(total_budget - expense, 0)
    daily_allowance = (budget_left / days_left) if days_left else 0
    over = max(projected - total_budget, 0) if total_budget else 0
    return ForecastOut(
        month=month,
        days_in_month=days,
        days_passed=days_passed,
        days_left=days_left,
        income=round(income, 2),
        expense=round(expense, 2),
        daily_average=round(daily_average, 2),
        projected_expense=round(projected, 2),
        total_budget=round(total_budget, 2),
        budget_left=round(budget_left, 2),
        daily_allowance=round(daily_allowance, 2),
        projected_over_budget=round(over, 2),
    )


@router.get("/categories", response_model=list[CategoryAgg])
def categories(type: str = Query(pattern="^(income|expense)$", default="expense"),
               date_from: date | None = None,
               date_to: date | None = None,
               user: models.User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    q = (db.query(
             func.coalesce(models.Category.name, "Без категории"),
             func.coalesce(func.sum(models.Operation.amount), 0))
         .outerjoin(models.Operation,
                    models.Operation.category_id == models.Category.id)
         .filter(models.Operation.user_id == user.id,
                 models.Operation.type == type)
         .group_by(models.Category.name))
    if date_from:
        q = q.filter(models.Operation.date >= date_from)
    if date_to:
        q = q.filter(models.Operation.date <= date_to)
    rows = q.all()
    total = sum(float(a) for _, a in rows) or 0
    result = []
    for name, amount in rows:
        amt = float(amount)
        result.append(CategoryAgg(category_id=None, category_name=name,
                                  amount=round(amt, 2),
                                  percent=round(amt / total * 100, 1) if total else 0))
    result.sort(key=lambda x: x.amount, reverse=True)
    return result
