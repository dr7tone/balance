"""Категории операций (стандартные и пользовательские)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..deps import get_current_user
from ..schemas import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(user: models.User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    return (db.query(models.Category)
            .filter(models.Category.user_id == user.id)
            .order_by(models.Category.is_default.desc(), models.Category.name)
            .all())


@router.post("", response_model=CategoryOut)
def create_category(data: CategoryCreate,
                    user: models.User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    exists = (db.query(models.Category)
              .filter(models.Category.user_id == user.id,
                      models.Category.name.ilike(data.name),
                      models.Category.type == data.type)
              .first())
    if exists:
        raise HTTPException(status_code=400, detail="Такая категория уже существует")
    cat = models.Category(user_id=user.id, name=data.name, type=data.type)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, data: CategoryUpdate,
                    user: models.User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    cat = db.get(models.Category, category_id)
    if cat is None or cat.user_id != user.id:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    cat.name = data.name
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int,
                    user: models.User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    cat = db.get(models.Category, category_id)
    if cat is None or cat.user_id != user.id:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    # операции остаются, но без категории; бюджеты удаляются
    (db.query(models.Operation)
     .filter(models.Operation.category_id == cat.id,
             models.Operation.user_id == user.id)
     .update({models.Operation.category_id: None}))
    (db.query(models.Budget)
     .filter(models.Budget.category_id == cat.id,
             models.Budget.user_id == user.id)
     .delete())
    db.delete(cat)
    db.commit()
