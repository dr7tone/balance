"""Цели накопления («мечты»): создание, пополнение вкладов, прогресс."""
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..deps import get_current_user
from ..schemas import (GoalContribute, GoalContributionOut, GoalCreate, GoalOut,
                       GoalUpdate, GoalWithdraw)
from ..seed import get_or_create_savings_category, get_or_create_withdraw_category

router = APIRouter(prefix="/goals", tags=["goals"])


def _to_goal_out(goal: models.Goal) -> GoalOut:
    target = float(goal.target_amount)
    saved = float(goal.saved_amount or 0)
    progress = round(saved / target * 100, 1) if target else 0
    return GoalOut(
        id=goal.id,
        name=goal.name,
        target_amount=target,
        saved_amount=round(saved, 2),
        progress_percent=progress,
        deadline=goal.deadline,
        created_at=goal.created_at,
    )


@router.get("", response_model=list[GoalOut])
def list_goals(user: models.User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    goals = (db.query(models.Goal)
             .filter(models.Goal.user_id == user.id)
             .order_by(models.Goal.created_at.desc())
             .all())
    return [_to_goal_out(g) for g in goals]


@router.post("", response_model=GoalOut)
def create_goal(data: GoalCreate,
                user: models.User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    goal = models.Goal(user_id=user.id, name=data.name,
                       target_amount=data.target_amount,
                       saved_amount=0, deadline=data.deadline)
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _to_goal_out(goal)


@router.patch("/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: int, data: GoalUpdate,
                user: models.User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    goal = db.get(models.Goal, goal_id)
    if goal is None or goal.user_id != user.id:
        raise HTTPException(status_code=404, detail="Цель не найдена")
    if "name" in data.model_fields_set and data.name is not None:
        goal.name = data.name
    if "target_amount" in data.model_fields_set and data.target_amount is not None:
        goal.target_amount = data.target_amount
    if "deadline" in data.model_fields_set:
        goal.deadline = data.deadline
    db.commit()
    db.refresh(goal)
    return _to_goal_out(goal)


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: int,
                user: models.User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    goal = db.get(models.Goal, goal_id)
    if goal is None or goal.user_id != user.id:
        raise HTTPException(status_code=404, detail="Цель не найдена")
    db.delete(goal)
    db.commit()


@router.post("/{goal_id}/contribute", response_model=GoalOut)
def contribute(goal_id: int, data: GoalContribute,
               user: models.User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    """Внести вклад в мечту: сумма фиксируется как расход «Накопления»."""
    goal = db.get(models.Goal, goal_id)
    if goal is None or goal.user_id != user.id:
        raise HTTPException(status_code=404, detail="Цель не найдена")

    goal.saved_amount = (goal.saved_amount or 0) + Decimal(str(data.amount))
    db.add(models.GoalContribution(goal_id=goal.id, amount=data.amount,
                                   note=data.note))

    savings_cat = get_or_create_savings_category(db, user.id)
    db.add(models.Operation(user_id=user.id,
                            type="expense",
                            amount=data.amount,
                            date=date.today(),
                            category_id=savings_cat.id,
                            comment=f"Накопление на мечту «{goal.name}»"))
    db.commit()
    db.refresh(goal)
    return _to_goal_out(goal)


@router.get("/{goal_id}/contributions", response_model=list[GoalContributionOut])
def list_contributions(goal_id: int,
                       user: models.User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    goal = db.get(models.Goal, goal_id)
    if goal is None or goal.user_id != user.id:
        raise HTTPException(status_code=404, detail="Цель не найдена")
    return (db.query(models.GoalContribution)
            .filter(models.GoalContribution.goal_id == goal_id)
            .order_by(models.GoalContribution.created_at.desc())
            .all())


@router.post("/{goal_id}/withdraw", response_model=GoalOut)
def withdraw(goal_id: int, data: GoalWithdraw,
             user: models.User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    """Снять часть накоплений: уменьшает прогресс и создаёт доход."""
    goal = db.get(models.Goal, goal_id)
    if goal is None or goal.user_id != user.id:
        raise HTTPException(status_code=404, detail="Цель не найдена")
    saved = float(goal.saved_amount or 0)
    if data.amount > saved:
        raise HTTPException(status_code=400,
                            detail="Нельзя снять больше, чем уже накоплено")
    goal.saved_amount = (goal.saved_amount or 0) - Decimal(str(data.amount))
    withdraw_cat = get_or_create_withdraw_category(db, user.id)
    db.add(models.Operation(user_id=user.id,
                            type="income",
                            amount=data.amount,
                            date=date.today(),
                            category_id=withdraw_cat.id,
                            comment=f"Снятие с мечты «{goal.name}»"))
    db.commit()
    db.refresh(goal)
    return _to_goal_out(goal)
