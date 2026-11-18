"""Операции доходов и расходов: CRUD, фильтры, экспорт/импорт CSV."""
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..schemas import OperationCreate, OperationOut, OperationPage, OperationUpdate
from ..services.csv_utils import build_csv, parse_csv

router = APIRouter(prefix="/operations", tags=["operations"])


def _to_out(op: models.Operation) -> OperationOut:
    return OperationOut(
        id=op.id,
        type=op.type,
        amount=float(op.amount),
        date=op.date,
        category_id=op.category_id,
        category_name=op.category.name if op.category else None,
        comment=op.comment or "",
        created_at=op.created_at,
    )


def _get_user_category(db: Session, user_id: int, category_id: int,
                       op_type: str | None = None) -> models.Category:
    cat = db.get(models.Category, category_id)
    if cat is None or cat.user_id != user_id:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    if op_type and cat.type != op_type:
        raise HTTPException(
            status_code=400,
            detail="Тип категории не совпадает с типом операции",
        )
    return cat


@router.get("", response_model=OperationPage)
def list_operations(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    type: str | None = Query(default=None, pattern="^(income|expense)$"),
    category_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    q = db.query(models.Operation).filter(models.Operation.user_id == user.id)
    if type:
        q = q.filter(models.Operation.type == type)
    if category_id:
        q = q.filter(models.Operation.category_id == category_id)
    if date_from:
        q = q.filter(models.Operation.date >= date_from)
    if date_to:
        q = q.filter(models.Operation.date <= date_to)
    if search:
        # SQLite не умеет Unicode-регистронезависимый LIKE (кириллица) —
        # в локальном режиме фильтруем на уровне Python, PostgreSQL использует ILIKE.
        if settings.database_url.startswith("sqlite"):
            search_lower = search.lower()
            matched_ids = [
                o.id for o in q.all()
                if search_lower in (o.comment or "").lower()
            ]
            q = q.filter(models.Operation.id.in_(matched_ids or [-1]))
        else:
            q = q.filter(models.Operation.comment.ilike(f"%{search}%"))

    total = q.count()
    items = (q.order_by(models.Operation.date.desc(),
                        models.Operation.id.desc())
             .offset(offset).limit(limit).all())
    return OperationPage(total=total, items=[_to_out(o) for o in items])


@router.post("", response_model=OperationOut)
def create_operation(data: OperationCreate,
                     user: models.User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    if data.category_id is not None:
        _get_user_category(db, user.id, data.category_id, data.type)
    op = models.Operation(user_id=user.id,
                          type=data.type,
                          amount=data.amount,
                          date=data.date,
                          category_id=data.category_id,
                          comment=data.comment)
    db.add(op)
    db.commit()
    db.refresh(op)
    return _to_out(op)


@router.put("/{operation_id}", response_model=OperationOut)
def update_operation(operation_id: int, data: OperationUpdate,
                     user: models.User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    op = db.get(models.Operation, operation_id)
    if op is None or op.user_id != user.id:
        raise HTTPException(status_code=404, detail="Операция не найдена")
    if data.category_id is not None:
        _get_user_category(db, user.id, data.category_id,
                           data.type or op.type)
    for field in ("type", "amount", "date", "comment"):
        value = getattr(data, field)
        if value is not None:
            setattr(op, field, value)
    if data.category_id is not None:
        op.category_id = data.category_id
    db.commit()
    db.refresh(op)
    return _to_out(op)


@router.delete("/{operation_id}", status_code=204)
def delete_operation(operation_id: int,
                     user: models.User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    op = db.get(models.Operation, operation_id)
    if op is None or op.user_id != user.id:
        raise HTTPException(status_code=404, detail="Операция не найдена")
    db.delete(op)
    db.commit()


@router.get("/export")
def export_csv(user: models.User = Depends(get_current_user),
               db: Session = Depends(get_db),
               date_from: date | None = None,
               date_to: date | None = None):
    q = db.query(models.Operation).filter(models.Operation.user_id == user.id)
    if date_from:
        q = q.filter(models.Operation.date >= date_from)
    if date_to:
        q = q.filter(models.Operation.date <= date_to)
    operations = q.order_by(models.Operation.date).all()
    csv_text = build_csv([
        {
            "date": o.date.isoformat(),
            "type": "доход" if o.type == "income" else "расход",
            "amount": float(o.amount),
            "category": o.category.name if o.category else "",
            "comment": o.comment or "",
        }
        for o in operations
    ])
    return Response(
        content="\ufeff" + csv_text,  # BOM для Excel
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=balance_operations.csv"},
    )


@router.post("/import")
def import_csv(file: UploadFile = File(...),
               user: models.User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    raw = file.file.read().decode("utf-8-sig", errors="replace")
    rows, errors = parse_csv(raw)
    created = 0
    for row in rows:
        cat = None
        if row["category"]:
            cat = (db.query(models.Category)
                   .filter(models.Category.user_id == user.id,
                           models.Category.name.ilike(row["category"]),
                           models.Category.type == row["type"])
                   .first())
            if cat is None and row["type"] == "expense":
                cat = (db.query(models.Category)
                       .filter(models.Category.user_id == user.id,
                               models.Category.name == "Прочее",
                               models.Category.type == "expense")
                       .first())
        db.add(models.Operation(user_id=user.id,
                                type=row["type"],
                                amount=row["amount"],
                                date=row["date"],
                                category_id=cat.id if cat else None,
                                comment=row["comment"]))
        created += 1
    db.commit()
    return {"imported": created, "skipped": len(errors),
            "errors": errors[:10], "total_errors": len(errors)}
