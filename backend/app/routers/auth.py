"""Регистрация, вход, текущий пользователь."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..deps import get_current_user
from ..schemas import PasswordChange, Token, UserCreate, UserOut, UserUpdate
from ..security import create_access_token, hash_password, verify_password
from ..seed import create_default_categories

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(status_code=400,
                            detail="Пользователь с таким e-mail уже зарегистрирован")
    user = models.User(email=data.email, username=data.username,
                       hashed_password=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    create_default_categories(db, user.id)
    return Token(access_token=create_access_token(user.id))


@router.post("/token", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный e-mail или пароль")
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(data: UserUpdate,
              user: models.User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    if data.email is not None and data.email != user.email:
        exists = (db.query(models.User)
                  .filter(models.User.email == data.email,
                          models.User.id != user.id)
                  .first())
        if exists:
            raise HTTPException(status_code=400,
                                detail="Этот e-mail уже занят другим пользователем")
        user.email = data.email
    if data.username is not None:
        user.username = data.username
    db.commit()
    db.refresh(user)
    return user


@router.post("/change-password")
def change_password(data: PasswordChange,
                    user: models.User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Текущий пароль указан неверно")
    if data.current_password == data.new_password:
        raise HTTPException(status_code=400, detail="Новый пароль должен отличаться от текущего")
    user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"ok": True}
