"""Начальные данные: стандартные категории, системная категория «Накопления»."""
from sqlalchemy.orm import Session

from . import models

DEFAULT_EXPENSE = ["Продукты", "Транспорт", "Связь", "Жильё", "Здоровье",
                   "Образование", "Одежда", "Развлечения", "Прочее"]
DEFAULT_INCOME = ["Зарплата", "Стипендия", "Подарки", "Подработка", "Прочее"]


def create_default_categories(db: Session, user_id: int) -> None:
    for name in DEFAULT_EXPENSE:
        db.add(models.Category(user_id=user_id, name=name, type="expense",
                               is_default=True, is_system=False))
    for name in DEFAULT_INCOME:
        db.add(models.Category(user_id=user_id, name=name, type="income",
                               is_default=True, is_system=False))
    db.commit()


def get_or_create_savings_category(db: Session, user_id: int) -> models.Category:
    """Категория «Накопления» для автоматического учёта вкладов в мечту."""
    cat = (db.query(models.Category)
           .filter(models.Category.user_id == user_id,
                   models.Category.name == "Накопления")
           .first())
    if cat is None:
        cat = models.Category(user_id=user_id, name="Накопления",
                              type="expense", is_default=False, is_system=True)
        db.add(cat)
        db.commit()
        db.refresh(cat)
    return cat


def get_or_create_withdraw_category(db: Session, user_id: int) -> models.Category:
    """Категория «Возврат накоплений» для снятия денег с мечты."""
    cat = (db.query(models.Category)
           .filter(models.Category.user_id == user_id,
                   models.Category.name == "Возврат накоплений")
           .first())
    if cat is None:
        cat = models.Category(user_id=user_id, name="Возврат накоплений",
                              type="income", is_default=False, is_system=True)
        db.add(cat)
        db.commit()
        db.refresh(cat)
    return cat


def find_category(db: Session, user_id: int, name: str, type_: str | None = None) -> models.Category | None:
    q = db.query(models.Category).filter(
        models.Category.user_id == user_id,
        models.Category.name.ilike(name))
    if type_:
        q = q.filter(models.Category.type == type_)
    return q.first()
