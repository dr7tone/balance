"""Pydantic-схемы API."""
from datetime import date as date_type, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Пользователи ----------
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    is_admin: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = Field(default=None, min_length=2, max_length=100)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


# ---------- Категории ----------
class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: str = Field(pattern="^(income|expense)$")


class CategoryUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    is_default: bool
    is_system: bool


# ---------- Операции ----------
class OperationCreate(BaseModel):
    type: str = Field(pattern="^(income|expense)$")
    amount: float = Field(gt=0)
    date: date_type
    category_id: int | None = None
    comment: str = Field(default="", max_length=500)


class OperationUpdate(BaseModel):
    type: str | None = Field(default=None, pattern="^(income|expense)$")
    amount: float | None = Field(default=None, gt=0)
    date: date_type | None = None
    category_id: int | None = None
    comment: str | None = Field(default=None, max_length=500)


class OperationOut(BaseModel):
    id: int
    type: str
    amount: float
    date: date_type
    category_id: int | None
    category_name: str | None
    comment: str
    created_at: datetime


class OperationPage(BaseModel):
    total: int
    items: list[OperationOut]


# ---------- Бюджеты ----------
class BudgetInput(BaseModel):
    category_id: int
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    limit_amount: float = Field(gt=0)


class BudgetStatusOut(BaseModel):
    budget_id: int
    category_id: int
    category_name: str
    month: str
    limit_amount: float
    spent: float
    remaining: float
    percent: float


# ---------- Цели (мечты) ----------
class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    target_amount: float = Field(gt=0)
    deadline: date_type | None = None


class GoalUpdate(BaseModel):
    name: str | None = None
    target_amount: float | None = Field(default=None, gt=0)
    deadline: date_type | None = None


class GoalOut(BaseModel):
    id: int
    name: str
    target_amount: float
    saved_amount: float
    progress_percent: float
    deadline: date_type | None
    created_at: datetime


class GoalContribute(BaseModel):
    amount: float = Field(gt=0)
    note: str = Field(default="", max_length=255)


class GoalWithdraw(BaseModel):
    amount: float = Field(gt=0)
    note: str = Field(default="", max_length=255)


class GoalContributionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: float
    note: str
    created_at: datetime


class BudgetCopy(BaseModel):
    from_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    to_month: str = Field(pattern=r"^\d{4}-\d{2}$")


class RecurringCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    type: str = Field(pattern="^(income|expense)$")
    amount: float = Field(gt=0)
    category_id: int | None = None
    next_date: date_type
    period: str = Field(default="monthly", pattern="^(monthly)$")
    is_active: bool = True


class RecurringUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    type: str | None = Field(default=None, pattern="^(income|expense)$")
    amount: float | None = Field(default=None, gt=0)
    category_id: int | None = None
    next_date: date_type | None = None
    period: str | None = Field(default=None, pattern="^(monthly)$")
    is_active: bool | None = None


class RecurringOut(BaseModel):
    id: int
    name: str
    type: str
    amount: float
    category_id: int | None
    category_name: str | None
    next_date: date_type
    period: str
    is_active: bool
    created_at: datetime


class RecurringPayOut(BaseModel):
    recurring: RecurringOut
    operation_id: int


class DailyPoint(BaseModel):
    date: date_type
    income: float
    expense: float


class ForecastOut(BaseModel):
    month: str
    days_in_month: int
    days_passed: int
    days_left: int
    income: float
    expense: float
    daily_average: float
    projected_expense: float
    total_budget: float
    budget_left: float
    daily_allowance: float
    projected_over_budget: float


class NotificationOut(BaseModel):
    id: str
    kind: str
    severity: str  # info / warning / danger / success
    title: str
    message: str
    link: str


# ---------- Аналитика ----------
class CategoryAgg(BaseModel):
    category_id: int | None
    category_name: str
    amount: float
    percent: float


class SummaryOut(BaseModel):
    income: float
    expense: float
    balance: float
    operations_count: int
    top_categories: list[CategoryAgg]


class MonthlyPoint(BaseModel):
    month: str
    income: float
    expense: float
    balance: float
