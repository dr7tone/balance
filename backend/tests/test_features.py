# -*- coding: utf-8 -*-
"""Тесты новых возможностей: демо-режим, регулярные платежи, профиль,
прогнозы и уведомления."""
from datetime import date, timedelta

from conftest import auth_headers


def test_demo_session_returns_populated_account(client):
    r = client.post("/api/demo/session")
    assert r.status_code == 200
    token = r.json()["access_token"]
    h = auth_headers(token)

    me = client.get("/api/auth/me", headers=h).json()
    assert me["email"] == "demo@balance.local"
    assert me["is_admin"] is True

    ops = client.get("/api/operations", headers=h, params={"limit": 5}).json()
    assert ops["total"] > 100
    assert len(client.get("/api/goals", headers=h).json()) >= 3
    assert len(client.get("/api/recurring", headers=h).json()) >= 3
    assert len(client.get("/api/notifications", headers=h).json()) >= 1

    # повторный вызов не дублирует данные
    client.post("/api/demo/session")
    ops2 = client.get("/api/operations", headers=h, params={"limit": 5}).json()
    assert ops2["total"] == ops["total"]


def test_profile_update_and_password_change(client, user_token):
    h = auth_headers(user_token)
    r = client.patch("/api/auth/me", headers=h, json={
        "username": "Новое имя", "email": "new@guap.ru"})
    assert r.status_code == 200
    assert r.json()["username"] == "Новое имя"
    assert r.json()["email"] == "new@guap.ru"

    r = client.post("/api/auth/change-password", headers=h, json={
        "current_password": "secret123", "new_password": "newsecret456"})
    assert r.status_code == 200

    r = client.post("/api/auth/token", data={
        "username": "new@guap.ru", "password": "newsecret456"})
    assert r.status_code == 200


def test_recurring_payment_pay_and_process(client, user_token):
    h = auth_headers(user_token)
    cats = client.get("/api/categories", headers=h).json()
    food = next(c for c in cats if c["name"] == "Продукты")
    today = date.today()

    r = client.post("/api/recurring", headers=h, json={
        "name": "Тестовая подписка", "type": "expense", "amount": 500,
        "category_id": food["id"], "next_date": today.isoformat()})
    assert r.status_code == 200
    item = r.json()
    assert item["next_date"] == today.isoformat()

    r = client.post(f"/api/recurring/{item['id']}/pay", headers=h)
    assert r.status_code == 200
    assert r.json()["recurring"]["next_date"] > today.isoformat()

    ops = client.get("/api/operations", headers=h).json()
    assert any(o["comment"] == "Регулярный платёж: Тестовая подписка"
               for o in ops["items"])

    r = client.post("/api/recurring/process-due", headers=h)
    assert r.status_code == 200
    assert "paid" in r.json()


def test_budget_copy(client, user_token):
    h = auth_headers(user_token)
    cats = client.get("/api/categories", headers=h).json()
    food = next(c for c in cats if c["name"] == "Продукты")
    client.post("/api/budgets", headers=h, json={
        "category_id": food["id"], "month": "2026-09", "limit_amount": 5000})

    r = client.post("/api/budgets/copy", headers=h, json={
        "from_month": "2026-09", "to_month": "2026-10"})
    assert r.status_code == 200
    assert r.json()["copied"] == 1

    status = client.get("/api/budgets/status", headers=h,
                        params={"month": "2026-10"}).json()
    assert status[0]["limit_amount"] == 5000


def test_goal_history_and_withdraw(client, user_token):
    h = auth_headers(user_token)
    goal = client.post("/api/goals", headers=h, json={
        "name": "Велосипед", "target_amount": 50000}).json()
    client.post(f"/api/goals/{goal['id']}/contribute", headers=h,
                json={"amount": 10000, "note": "первый вклад"})

    history = client.get(f"/api/goals/{goal['id']}/contributions", headers=h).json()
    assert len(history) == 1
    assert history[0]["amount"] == 10000

    r = client.post(f"/api/goals/{goal['id']}/withdraw", headers=h,
                    json={"amount": 4000, "note": "снятие"})
    assert r.status_code == 200
    assert r.json()["saved_amount"] == 6000

    r = client.post(f"/api/goals/{goal['id']}/withdraw", headers=h,
                    json={"amount": 999999})
    assert r.status_code == 400


def test_analytics_daily_forecast_and_notifications(client, user_token):
    h = auth_headers(user_token)
    cats = client.get("/api/categories", headers=h).json()
    food = next(c for c in cats if c["name"] == "Продукты")
    today = date.today()
    month = today.strftime("%Y-%m")

    client.post("/api/operations", headers=h, json={
        "type": "expense", "amount": 1500, "date": today.isoformat(),
        "category_id": food["id"], "comment": "тест"})
    client.post("/api/budgets", headers=h, json={
        "category_id": food["id"], "month": month, "limit_amount": 1000})

    daily = client.get("/api/analytics/daily", headers=h,
                       params={"month": month}).json()
    assert len(daily) >= 28
    assert sum(p["expense"] for p in daily) == 1500

    forecast = client.get("/api/analytics/forecast", headers=h,
                          params={"month": month}).json()
    assert forecast["expense"] == 1500
    assert forecast["total_budget"] == 1000
    assert forecast["daily_allowance"] >= 0

    notes = client.get("/api/notifications", headers=h).json()
    assert any(n["kind"] == "budget" for n in notes)

    # регулярный платёж через 3 дня попадает в уведомления
    client.post("/api/recurring", headers=h, json={
        "name": "Скоро списание", "type": "expense", "amount": 100,
        "category_id": food["id"],
        "next_date": (today + timedelta(days=3)).isoformat()})
    notes = client.get("/api/notifications", headers=h).json()
    assert any(n["kind"] == "recurring" for n in notes)
