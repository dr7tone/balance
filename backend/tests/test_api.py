# -*- coding: utf-8 -*-
"""Интеграционные тесты API BALANCE."""
from conftest import auth_headers


def test_register_and_login(client):
    r = client.post("/api/auth/register", json={
        "email": "user1@test.ru", "username": "Иван", "password": "qwerty123"})
    assert r.status_code == 200
    assert r.json()["access_token"]

    # дубликат — ошибка
    r = client.post("/api/auth/register", json={
        "email": "user1@test.ru", "username": "Иван", "password": "qwerty123"})
    assert r.status_code == 400

    # вход
    r = client.post("/api/auth/token",
                    data={"username": "user1@test.ru", "password": "qwerty123"})
    assert r.status_code == 200
    assert r.json()["access_token"]

    r = client.post("/api/auth/token",
                    data={"username": "user1@test.ru", "password": "badpass"})
    assert r.status_code == 401


def test_default_categories_seeded(client, user_token):
    r = client.get("/api/categories", headers=auth_headers(user_token))
    assert r.status_code == 200
    cats = r.json()
    assert len(cats) >= 10
    types = {c["type"] for c in cats}
    assert types == {"income", "expense"}


def test_operations_crud_and_filters(client, user_token):
    h = auth_headers(user_token)
    cats = client.get("/api/categories", headers=h).json()
    food = next(c for c in cats if c["name"] == "Продукты")
    salary = next(c for c in cats if c["name"] == "Зарплата")

    r = client.post("/api/operations", headers=h, json={
        "type": "expense", "amount": 1500.50, "date": "2026-10-05",
        "category_id": food["id"], "comment": "Продукты на неделю"})
    assert r.status_code == 200
    op_id = r.json()["id"]
    assert r.json()["category_name"] == "Продукты"

    client.post("/api/operations", headers=h, json={
        "type": "income", "amount": 50000, "date": "2026-10-01",
        "category_id": salary["id"], "comment": "Зарплата"})

    r = client.get("/api/operations", headers=h)
    assert r.json()["total"] == 2

    r = client.get("/api/operations", headers=h, params={"type": "expense"})
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["amount"] == 1500.5

    r = client.get("/api/operations", headers=h,
                   params={"search": "зарплат", "type": "income"})
    assert r.json()["total"] == 1

    r = client.put(f"/api/operations/{op_id}", headers=h,
                   json={"amount": 1600})
    assert r.status_code == 200
    assert r.json()["amount"] == 1600

    r = client.delete(f"/api/operations/{op_id}", headers=h)
    assert r.status_code == 204


def test_summary_and_monthly(client, user_token):
    h = auth_headers(user_token)
    cats = client.get("/api/categories", headers=h).json()
    food = next(c for c in cats if c["name"] == "Продукты")
    salary = next(c for c in cats if c["name"] == "Зарплата")

    client.post("/api/operations", headers=h, json={
        "type": "expense", "amount": 1000, "date": "2026-10-05",
        "category_id": food["id"], "comment": "продукты"})
    client.post("/api/operations", headers=h, json={
        "type": "income", "amount": 10000, "date": "2026-10-01",
        "category_id": salary["id"], "comment": "зарплата"})

    r = client.get("/api/analytics/summary", headers=h,
                   params={"date_from": "2026-10-01", "date_to": "2026-10-31"})
    s = r.json()
    assert s["income"] == 10000
    assert s["expense"] == 1000
    assert s["balance"] == 9000
    assert s["top_categories"][0]["category_name"] == "Продукты"

    r = client.get("/api/analytics/categories", headers=h, params={"type": "expense"})
    cats_agg = r.json()
    assert any(c["category_name"] == "Продукты" for c in cats_agg)
    assert sum(c["amount"] for c in cats_agg) == 1000

    r = client.get("/api/analytics/monthly", headers=h, params={"months": 3})
    months = r.json()
    assert len(months) == 3
    assert months[-1]["month"] == "2026-10"


def test_budgets(client, user_token):
    h = auth_headers(user_token)
    cats = client.get("/api/categories", headers=h).json()
    food = next(c for c in cats if c["name"] == "Продукты")

    client.post("/api/operations", headers=h, json={
        "type": "expense", "amount": 3000, "date": "2026-10-10",
        "category_id": food["id"], "comment": "очередная закупка"})

    r = client.post("/api/budgets", headers=h, json={
        "category_id": food["id"], "month": "2026-10", "limit_amount": 4000})
    assert r.status_code == 200

    r = client.get("/api/budgets/status", headers=h, params={"month": "2026-10"})
    item = r.json()[0]
    assert item["limit_amount"] == 4000
    assert item["spent"] == 3000
    assert item["remaining"] == 1000
    assert item["percent"] == 75.0


def test_goals_contribute_creates_savings_operation(client, user_token):
    h = auth_headers(user_token)
    r = client.post("/api/goals", headers=h, json={
        "name": "Новый ноутбук", "target_amount": 80000, "deadline": "2027-01-01"})
    assert r.status_code == 200
    goal = r.json()
    assert goal["saved_amount"] == 0
    assert goal["progress_percent"] == 0

    r = client.post(f"/api/goals/{goal['id']}/contribute", headers=h,
                    json={"amount": 15000, "note": "первый вклад"})
    g = r.json()
    assert g["saved_amount"] == 15000
    assert g["progress_percent"] == 18.8

    # автоматически создана операция «Накопления»
    r = client.get("/api/operations", headers=h, params={"type": "expense"})
    ops = r.json()["items"]
    assert any(o["category_name"] == "Накопления" and o["amount"] == 15000 for o in ops)

    # повторный вклад
    client.post(f"/api/goals/{goal['id']}/contribute", headers=h,
                json={"amount": 5000})
    r = client.get("/api/goals", headers=h)
    g = next(x for x in r.json() if x["id"] == goal["id"])
    assert g["saved_amount"] == 20000

    r = client.delete(f"/api/goals/{goal['id']}", headers=h)
    assert r.status_code == 204


def test_csv_export_import(client, user_token):
    h = auth_headers(user_token)
    cats = client.get("/api/categories", headers=h).json()
    salary = next(c for c in cats if c["name"] == "Зарплата")
    client.post("/api/operations", headers=h, json={
        "type": "income", "amount": 20000, "date": "2026-10-01",
        "category_id": salary["id"], "comment": "октябрь"})

    r = client.get("/api/operations/export", headers=h)
    assert r.status_code == 200
    assert "Дата;Тип;Сумма" in r.text

    csv_content = (
        "Дата;Тип;Сумма;Категория;Комментарий\n"
        "2026-11-01;доход;3000;Подработка;проект\n"
        "01.11.2026;расход;500;Транспорт;билет\n"
    )
    r = client.post("/api/operations/import", headers=h,
                    files={"file": ("data.csv", csv_content.encode("utf-8"),
                                    "text/csv")})
    assert r.status_code == 200
    assert r.json()["imported"] == 2
    assert r.json()["skipped"] == 0

    r = client.get("/api/operations", headers=h, params={"date_from": "2026-11-01"})
    assert r.json()["total"] == 2


def test_admin_role_management(client):
    r = client.post("/api/auth/register", json={
        "email": "admin@test.ru", "username": "Админ", "password": "admin123"})
    admin_token = r.json()["access_token"]

    r = client.post("/api/auth/register", json={
        "email": "user2@test.ru", "username": "Петя",
        "password": "petia123"})
    user2_token = r.json()["access_token"]

    # обычный пользователь не имеет доступа к админке
    r = client.get("/api/admin/users", headers=auth_headers(user2_token))
    assert r.status_code == 403

    # первый зарегистрированный пользователь — не админ
    r = client.get("/api/admin/users", headers=auth_headers(admin_token))
    assert r.status_code == 403

    # назначаем админа напрямую через БД (в проде — первичный админ)
    from app.database import SessionLocal
    from app import models
    db = SessionLocal()
    u = db.query(models.User).filter(models.User.email == "admin@test.ru").first()
    u.is_admin = True
    db.commit()
    db.close()

    r = client.get("/api/admin/users", headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert len(r.json()) >= 2  # админ + обычный пользователь из этого теста

    users = r.json()
    target = next(x for x in users if x["email"] == "user2@test.ru")
    r = client.patch(f"/api/admin/users/{target['id']}", headers=auth_headers(admin_token),
                     json={"is_admin": True})
    assert r.status_code == 200
    assert r.json()["is_admin"] is True

    # запрет снятия админа с себя
    me = next(x for x in client.get("/api/admin/users",
                                    headers=auth_headers(admin_token)).json()
              if x["email"] == "admin@test.ru")
    r = client.patch(f"/api/admin/users/{me['id']}", headers=auth_headers(admin_token),
                     json={"is_admin": False})
    assert r.status_code == 400
