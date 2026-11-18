"""Демо-режим: быстрый вход с подготовленными данными для показа."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..demo import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user, reset_demo_user
from ..models import User
from ..deps import get_current_user
from ..schemas import Token
from ..security import create_access_token

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/info")
def demo_info():
    return {
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD,
        "enabled": True,
        "description": "Демо-аккаунт с историей операций, бюджетами, целями и регулярными платежами",
    }


@router.post("/session", response_model=Token)
def demo_session(db: Session = Depends(get_db)):
    user = ensure_demo_user(db)
    return Token(access_token=create_access_token(user.id))


@router.post("/reset", response_model=Token)
def demo_reset(user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    if user.email != DEMO_EMAIL:
        raise HTTPException(status_code=403,
                            detail="Сброс доступен только для демо-аккаунта")
    fresh = reset_demo_user(db)
    return Token(access_token=create_access_token(fresh.id))
