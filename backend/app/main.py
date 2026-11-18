"""Точка входа приложения BALANCE (FastAPI)."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import (admin, analytics, auth, budgets, categories, demo, goals,
                      notifications, operations, recurring)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="BALANCE API — учёт личных доходов и расходов",
    description="Веб-сервис учёта личных доходов и расходов «Баланс» (BALANCE). "
                "Возможности: операции, категории, бюджет, накопление на мечту, "
                "регулярные платежи, прогноз, уведомления и аналитика.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (auth.router, categories.router, operations.router,
               budgets.router, goals.router, recurring.router,
               analytics.router, notifications.router, demo.router,
               admin.router):
    app.include_router(router, prefix=settings.api_prefix)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}
