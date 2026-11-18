"""Демонстрационные данные для показа сервиса комиссии.

Демо-аккаунт создаётся по запросу с главной страницы входа и содержит
несколько месяцев реалистичных операций, бюджеты, цели и регулярные платежи.
"""
import calendar
import random
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from . import models
from .security import hash_password
from .seed import (DEFAULT_EXPENSE, DEFAULT_INCOME, create_default_categories,
                   get_or_create_savings_category)

DEMO_EMAIL = "demo@balance.local"
DEMO_PASSWORD = "demo1234"
DEMO_USERNAME = "Демо"
DEMO_SECOND_EMAIL = "anna@balance.local"
DEMO_THIRD_EMAIL = "maksim@balance.local"


def _shift_month(value: date, months: int) -> date:
    year = value.year + (value.month - 1 + months) // 12
    month = (value.month - 1 + months) % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _rng_money(rng: random.Random, low: float, high: float, step: int = 10) -> float:
    return float(round(rng.uniform(low, high) / step) * step)


def _find(db: Session, user_id: int, name: str) -> models.Category | None:
    return (db.query(models.Category)
            .filter(models.Category.user_id == user_id,
                    models.Category.name == name)
            .first())


def _operation(db: Session, user_id: int, category: models.Category | None,
               op_type: str, amount: float, day: date, comment: str) -> None:
    db.add(models.Operation(
        user_id=user_id,
        type=op_type,
        amount=amount,
        date=day,
        category_id=category.id if category else None,
        comment=comment,
    ))


def _create_operations(db: Session, user: models.User, rng: random.Random) -> None:
    today = date.today()
    extra_expense = ["Кафе", "Путешествия", "Подписки", "Питомцы"]
    for name in extra_expense:
        db.add(models.Category(user_id=user.id, name=name, type="expense"))
    db.add(models.Category(user_id=user.id, name="Инвестиции", type="income"))
    db.add(models.Category(user_id=user.id, name="Кэшбэк", type="income"))
    db.commit()

    cats = {c.name: c for c in db.query(models.Category)
            .filter(models.Category.user_id == user.id).all()}

    for offset in range(7, -1, -1):
        month_start = _shift_month(today.replace(day=1), -offset)
        last_day = calendar.monthrange(month_start.year, month_start.month)[1]
        month_end = date(month_start.year, month_start.month, last_day)
        if offset == 0:
            month_end = today
        if month_start > today:
            continue

        def day(d: int) -> date | None:
            if d > month_end.day:
                return None
            return date(month_start.year, month_start.month, d)

        salary = day(5)
        if salary:
            _operation(db, user.id, cats.get("Зарплата"), "income",
                       98000 + rng.choice([0, 0, 3000, 5000]), salary,
                       "Зарплата за месяц")
        for _ in range(rng.randint(1, 2)):
            d = day(rng.randint(6, 24))
            if d:
                _operation(db, user.id, cats.get("Подработка"), "income",
                           _rng_money(rng, 8000, 22000, 100), d,
                           rng.choice(["Фриланс-проект", "Консультация",
                                       "Оплата за подработку"]))
        d = day(rng.randint(15, 27))
        if d:
            _operation(db, user.id, cats.get("Кэшбэк"), "income",
                       _rng_money(rng, 320, 1600, 10), d, "Кэшбэк по карте")

        rent = day(10)
        if rent:
            _operation(db, user.id, cats.get("Жильё"), "expense", 28000,
                       rent, "Аренда квартиры")
        utilities = day(12)
        if utilities:
            _operation(db, user.id, cats.get("Жильё"), "expense",
                       _rng_money(rng, 3800, 5200, 10), utilities,
                       "Коммунальные услуги")
        internet = day(15)
        if internet:
            _operation(db, user.id, cats.get("Связь"), "expense", 900,
                       internet, "Домашний интернет")
        mobile = day(18)
        if mobile:
            _operation(db, user.id, cats.get("Связь"), "expense", 650,
                       mobile, "Мобильная связь")

        for _ in range(rng.randint(5, 8)):
            d = day(rng.randint(1, 28))
            if d:
                _operation(db, user.id, cats.get("Продукты"), "expense",
                           _rng_money(rng, 1200, 4200, 10), d,
                           rng.choice(["Продукты на неделю", "Супермаркет",
                                       "Пятёрочка", "Ашан", "Фрукты и овощи"]))
        for _ in range(rng.randint(3, 5)):
            d = day(rng.randint(2, 28))
            if d:
                _operation(db, user.id, cats.get("Кафе"), "expense",
                           _rng_money(rng, 350, 1900, 10), d,
                           rng.choice(["Кофе с коллегами", "Обед в кафе",
                                       "Доставка еды", "Пекарня"]))
        for _ in range(rng.randint(4, 7)):
            d = day(rng.randint(1, 28))
            if d:
                _operation(db, user.id, cats.get("Транспорт"), "expense",
                           _rng_money(rng, 150, 1100, 10), d,
                           rng.choice(["Метро", "Такси", "Автобус", "Каршеринг"]))
        for _ in range(rng.randint(1, 3)):
            d = day(rng.randint(4, 27))
            if d:
                _operation(db, user.id, cats.get("Развлечения"), "expense",
                           _rng_money(rng, 900, 4800, 100), d,
                           rng.choice(["Кино", "Концерт", "Настольные игры",
                                       "Прогулка и кофе"]))
        for _ in range(rng.randint(0, 2)):
            d = day(rng.randint(6, 26))
            if d:
                _operation(db, user.id, cats.get("Здоровье"), "expense",
                           _rng_money(rng, 700, 5200, 100), d,
                           rng.choice(["Аптека", "Приём врача", "Анализы",
                                       "Витамины"]))
        for _ in range(rng.randint(0, 2)):
            d = day(rng.randint(5, 25))
            if d:
                _operation(db, user.id, cats.get("Одежда"), "expense",
                           _rng_money(rng, 1800, 9000, 100), d,
                           rng.choice(["Кроссовки", "Джинсы", "Куртка",
                                       "Футболки"]))
        subs = day(5)
        if subs:
            _operation(db, user.id, cats.get("Подписки"), "expense", 399,
                       subs, "Яндекс Плюс")
        subs2 = day(20)
        if subs2:
            _operation(db, user.id, cats.get("Подписки"), "expense", 499,
                       subs2, "Онлайн-кинотеатр")
        pets = day(14)
        if pets:
            _operation(db, user.id, cats.get("Питомцы"), "expense",
                       _rng_money(rng, 900, 2800, 10), pets, "Корм для кота")
        other = day(rng.randint(3, 27))
        if other:
            _operation(db, user.id, cats.get("Прочее"), "expense",
                       _rng_money(rng, 500, 3500, 10), other,
                       rng.choice(["Подарок", "Хозтовары", "Книги", "Мелкие покупки"]))


def _create_budgets(db: Session, user: models.User) -> None:
    today = date.today()
    months = [_shift_month(today.replace(day=1), -1).strftime("%Y-%m"),
              today.strftime("%Y-%m")]
    limits = {
        "Продукты": 20000,
        "Кафе": 6000,
        "Транспорт": 6000,
        "Развлечения": 10000,
        "Жильё": 30000,
        "Здоровье": 6000,
    }
    for month in months:
        for name, limit in limits.items():
            cat = _find(db, user.id, name)
            if cat:
                db.add(models.Budget(user_id=user.id, category_id=cat.id,
                                     month=month, limit_amount=limit))
    db.commit()


def _create_goal(db: Session, user: models.User, name: str, target: float,
                 saved: float, deadline: date | None, rng: random.Random,
                 months_ago: int = 5) -> models.Goal:
    created = datetime.combine(
        _shift_month(date.today() - timedelta(days=months_ago * 30), 0),
        datetime.min.time(),
    )
    goal = models.Goal(user_id=user.id, name=name, target_amount=target,
                       saved_amount=saved, deadline=deadline, created_at=created)
    db.add(goal)
    db.flush()

    savings = get_or_create_savings_category(db, user.id)
    parts = 3
    if saved > 0:
        chunk = round(saved / parts, 2)
        for i in range(parts):
            amount = chunk if i < parts - 1 else saved - chunk * (parts - 1)
            # Вклады делаем в прошлых месяцах, чтобы текущий месяц
            # демонстрировал «живые» траты, а не только накопления.
            when = date.today() - timedelta(days=(parts - i) * 35 + rng.randint(0, 5))
            db.add(models.GoalContribution(
                goal_id=goal.id, amount=amount,
                note=["Первый вклад", "Пополнение", "Отложено с зарплаты"][i % 3],
                created_at=datetime.combine(when, datetime.min.time()),
            ))
            _operation(db, user.id, savings, "expense", amount, when,
                       f"Накопление на мечту «{name}»")
    return goal


def _create_goals(db: Session, user: models.User, rng: random.Random) -> None:
    today = date.today()
    _create_goal(db, user, "MacBook Pro", 180000, 96000,
                 today + timedelta(days=120), rng)
    _create_goal(db, user, "Отпуск на море", 150000, 60000,
                 today + timedelta(days=210), rng)
    _create_goal(db, user, "Новый iPhone", 90000, 90000,
                 today + timedelta(days=40), rng, months_ago=7)
    _create_goal(db, user, "Подушка безопасности", 300000, 45000, None, rng)
    db.commit()


def _create_recurring(db: Session, user: models.User) -> None:
    today = date.today()
    next_month = _shift_month(today.replace(day=1), 1)

    def at_next(day_num: int) -> date:
        day_num = min(day_num, calendar.monthrange(next_month.year,
                                                   next_month.month)[1])
        return date(next_month.year, next_month.month, day_num)

    plans = [
        ("Зарплата", "income", 98000, "Зарплата", at_next(5)),
        ("Аренда квартиры", "expense", 28000, "Жильё", at_next(10)),
        ("Интернет", "expense", 900, "Связь", at_next(15)),
        ("Спортзал", "expense", 2900, "Здоровье", at_next(20)),
        ("Яндекс Плюс", "expense", 399, "Подписки",
         today + timedelta(days=5)),
    ]
    for name, op_type, amount, cat_name, next_date in plans:
        cat = _find(db, user.id, cat_name)
        db.add(models.RecurringPayment(
            user_id=user.id, name=name, type=op_type, amount=amount,
            category_id=cat.id if cat else None, next_date=next_date,
            period="monthly", is_active=True,
        ))
    db.commit()


def _create_extra_users(db: Session) -> None:
    now = datetime.utcnow()
    for email, username, days_ago in [
        (DEMO_SECOND_EMAIL, "Анна Смирнова", 24),
        (DEMO_THIRD_EMAIL, "Максим Орлов", 9),
    ]:
        if db.query(models.User).filter(models.User.email == email).first():
            continue
        user = models.User(email=email, username=username,
                           hashed_password=hash_password("demo1234"),
                           created_at=now - timedelta(days=days_ago))
        db.add(user)
        db.commit()
        db.refresh(user)
        create_default_categories(db, user.id)


def ensure_demo_user(db: Session) -> models.User:
    user = (db.query(models.User)
            .filter(models.User.email == DEMO_EMAIL)
            .first())
    if user is not None:
        return user

    user = models.User(email=DEMO_EMAIL, username=DEMO_USERNAME,
                       hashed_password=hash_password(DEMO_PASSWORD),
                       is_admin=True,
                       created_at=datetime.utcnow() - timedelta(days=210))
    db.add(user)
    db.commit()
    db.refresh(user)
    create_default_categories(db, user.id)

    rng = random.Random(2026)
    _create_operations(db, user, rng)
    _create_budgets(db, user)
    _create_goals(db, user, rng)
    _create_recurring(db, user)
    _create_extra_users(db)
    db.commit()
    return user


def reset_demo_user(db: Session) -> models.User:
    user = (db.query(models.User)
            .filter(models.User.email == DEMO_EMAIL)
            .first())
    if user is not None:
        db.delete(user)
        db.commit()
    return ensure_demo_user(db)


def default_category_names() -> tuple[list[str], list[str]]:
    return DEFAULT_EXPENSE, DEFAULT_INCOME
