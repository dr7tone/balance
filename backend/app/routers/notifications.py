"""Персональные уведомления: бюджет, сроки целей, ближайшие платежи."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..deps import get_current_user
from ..schemas import NotificationOut
from .budgets import _spent_for_category

router = APIRouter(prefix="/notifications", tags=["notifications"])

_SEVERITY_ORDER = {"danger": 0, "warning": 1, "info": 2, "success": 3}


def _money(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ") + " ₽"


@router.get("", response_model=list[NotificationOut])
def notifications(user: models.User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    today = date.today()
    month = f"{today.year:04d}-{today.month:02d}"
    items: list[NotificationOut] = []

    budgets = (db.query(models.Budget)
               .filter(models.Budget.user_id == user.id,
                       models.Budget.month == month)
               .all())
    for b in budgets:
        spent = _spent_for_category(db, user.id, b.category_id, month)
        limit = float(b.limit_amount)
        percent = round(spent / limit * 100, 1) if limit else 0
        cat = db.get(models.Category, b.category_id)
        name = cat.name if cat else "Категория"
        if percent >= 100:
            items.append(NotificationOut(
                id=f"budget-over-{b.id}", kind="budget", severity="danger",
                title=f"Лимит «{name}» превышен",
                message=f"Потрачено {_money(spent)} из {_money(limit)} ({percent:.0f}%).",
                link="/budgets"))
        elif percent >= 80:
            items.append(NotificationOut(
                id=f"budget-warn-{b.id}", kind="budget", severity="warning",
                title=f"Бюджет «{name}» почти исчерпан",
                message=f"Использовано {percent:.0f}% лимита. Осталось {_money(max(limit - spent, 0))}.",
                link="/budgets"))
    if not budgets:
        items.append(NotificationOut(
            id="budget-none", kind="budget", severity="info",
            title="Бюджет на месяц не задан",
            message="Установите лимиты по категориям, чтобы контролировать расходы.",
            link="/budgets"))

    goals = (db.query(models.Goal)
             .filter(models.Goal.user_id == user.id)
             .all())
    for g in goals:
        if g.deadline is None:
            continue
        days = (g.deadline - today).days
        progress = (float(g.saved_amount or 0) / float(g.target_amount) * 100
                    if float(g.target_amount) else 0)
        if 0 <= days <= 30 and progress < 100:
            left = float(g.target_amount) - float(g.saved_amount or 0)
            items.append(NotificationOut(
                id=f"goal-deadline-{g.id}", kind="goal", severity="warning",
                title=f"До цели «{g.name}» осталось {days} дн.",
                message=f"Не хватает {_money(left)}. Успейте пополнить накопления.",
                link="/goals"))

    soon = today + timedelta(days=7)
    recurring = (db.query(models.RecurringPayment)
                 .filter(models.RecurringPayment.user_id == user.id,
                         models.RecurringPayment.is_active.is_(True),
                         models.RecurringPayment.next_date <= soon)
                 .order_by(models.RecurringPayment.next_date)
                 .all())
    for r in recurring:
        when = "сегодня" if r.next_date == today else (
            "завтра" if r.next_date == today + timedelta(days=1)
            else r.next_date.strftime("%d.%m"))
        label = "Списание" if r.type == "expense" else "Поступление"
        items.append(NotificationOut(
            id=f"recurring-{r.id}", kind="recurring", severity="info",
            title=f"{label}: {r.name}",
            message=f"{_money(float(r.amount))} · {when}",
            link="/recurring"))

    items.sort(key=lambda n: (_SEVERITY_ORDER.get(n.severity, 9), n.title))
    return items[:12]
