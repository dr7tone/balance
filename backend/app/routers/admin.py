"""Администрирование: список пользователей, назначение ролей."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..deps import get_current_admin
from ..schemas import UserOut

router = APIRouter(prefix="/admin", tags=["admin"])


class RoleUpdate(BaseModel):
    is_admin: bool


@router.get("/users", response_model=list[UserOut])
def list_users(_: models.User = Depends(get_current_admin),
               db: Session = Depends(get_db)):
    return (db.query(models.User)
            .order_by(models.User.created_at.desc())
            .all())


@router.patch("/users/{user_id}", response_model=UserOut)
def set_role(user_id: int, data: RoleUpdate,
             admin: models.User = Depends(get_current_admin),
             db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if user.id == admin.id and not data.is_admin:
        raise HTTPException(status_code=400,
                            detail="Нельзя снять права администратора с самого себя")
    user.is_admin = data.is_admin
    db.commit()
    db.refresh(user)
    return user
