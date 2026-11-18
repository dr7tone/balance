"""Модели базы данных: пользователи, категории, операции, бюджеты, цели (мечты)."""
from datetime import date as date_type, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    categories: Mapped[list["Category"]] = relationship(
        back_populates="user", cascade="all, delete-orphan")
    operations: Mapped[list["Operation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan")
    budgets: Mapped[list["Budget"]] = relationship(
        back_populates="user", cascade="all, delete-orphan")
    goals: Mapped[list["Goal"]] = relationship(
        back_populates="user", cascade="all, delete-orphan")
    recurring: Mapped[list["RecurringPayment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(10))  # income / expense
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)  # напр. «Накопления»

    user: Mapped["User"] = relationship(back_populates="categories")
    operations: Mapped[list["Operation"]] = relationship(
        back_populates="category", passive_deletes=True)


class Operation(Base):
    __tablename__ = "operations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(10))  # income / expense
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    date: Mapped[date_type] = mapped_column(Date, index=True)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="operations")
    category: Mapped["Category | None"] = relationship(back_populates="operations")


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint("user_id", "category_id", "month", name="uq_budget"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True)
    month: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    limit_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    user: Mapped["User"] = relationship(back_populates="budgets")


class Goal(Base):
    """Цель накопления («мечта»): название, необходимая сумма, накоплено, срок."""

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    target_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    saved_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    deadline: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="goals")
    contributions: Mapped[list["GoalContribution"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan")


class GoalContribution(Base):
    __tablename__ = "goal_contributions"

    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(
        ForeignKey("goals.id", ondelete="CASCADE"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    note: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    goal: Mapped["Goal"] = relationship(back_populates="contributions")


class RecurringPayment(Base):
    """Регулярный платёж (подписка, аренда, зарплата и т. п.)."""

    __tablename__ = "recurring_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    type: Mapped[str] = mapped_column(String(10))  # income / expense
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    next_date: Mapped[date_type] = mapped_column(Date, index=True)
    period: Mapped[str] = mapped_column(String(10), default="monthly")  # monthly
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="recurring")
    category: Mapped["Category | None"] = relationship()
