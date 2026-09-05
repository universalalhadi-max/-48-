"""
مخططات Pydantic — تحدّد شكل البيانات المقبولة في كل طلب، وشكل الرد المُعاد.
FastAPI يستخدمها تلقائياً للتحقق من صحة المدخلات ولإظهار توثيق تفاعلي على /docs.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator


def normalize_phone(v: str) -> str:
    digits = "".join(ch for ch in (v or "") if ch.isdigit())
    if digits.startswith("967"):
        digits = digits[3:]
    return digits


# ---------- المصادقة ----------
class LoginRequest(BaseModel):
    phone: str
    password: str
    device_id: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def _norm(cls, v):
        return normalize_phone(v)


class LoginResponse(BaseModel):
    token: str
    phone: str
    name: str
    role: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ---------- المستخدمون ----------
class UserOut(BaseModel):
    id: str
    phone: str
    name: str
    role: str
    protected: bool
    device_bound: bool  # true إن كان مرتبطاً بجهاز فعلاً (بدون كشف device_id نفسه)

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    phone: str
    name: str
    password: str
    role: str = "collector"

    @field_validator("phone")
    @classmethod
    def _norm(cls, v):
        return normalize_phone(v)

    @field_validator("role")
    @classmethod
    def _role(cls, v):
        if v not in ("admin", "collector"):
            raise ValueError("role must be admin or collector")
        return v


class UserUpdate(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None

    @field_validator("role")
    @classmethod
    def _role(cls, v):
        if v is not None and v not in ("admin", "collector"):
            raise ValueError("role must be admin or collector")
        return v


# ---------- المستأجرون ----------
class TenantOut(BaseModel):
    id: str
    shop: str
    name: str
    phone: Optional[str] = None
    rent: float
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantCreate(BaseModel):
    shop: str
    name: str
    phone: Optional[str] = None
    rent: float = 0


class TenantUpdate(BaseModel):
    shop: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    rent: Optional[float] = None


# ---------- عمليات التحصيل ----------
class RecordIn(BaseModel):
    """السجل كما يُنشئه التطبيق في الجهاز (يشمل id الذي وُلِّد محلياً)."""
    id: str
    tenant_id: str
    tenant_name: str
    shop: str
    amount: float
    date: datetime
    collector_name: Optional[str] = None
    collector_phone: Optional[str] = None


class RecordOut(BaseModel):
    id: str
    tenant_id: str
    tenant_name: str
    shop: str
    amount: float
    date: datetime
    collector_name: Optional[str] = None
    collector_phone: Optional[str] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecordEdit(BaseModel):
    amount: float
    date: datetime
    reason: str


class RecordDelete(BaseModel):
    reason: str


# ---------- سجل التعديلات ----------
class AuditOut(BaseModel):
    id: str
    at: datetime
    by_name: Optional[str] = None
    by_phone: Optional[str] = None
    action: str
    record_id: str
    tenant_name: Optional[str] = None
    shop: Optional[str] = None
    old_amount: Optional[float] = None
    new_amount: Optional[float] = None
    old_date: Optional[datetime] = None
    new_date: Optional[datetime] = None
    reason: str

    model_config = ConfigDict(from_attributes=True)


# ---------- المزامنة ----------
class SyncResponse(BaseModel):
    server_time: datetime
    tenants: List[TenantOut]
    records: List[RecordOut]
    users: List[UserOut] = []
    audit_log: List[AuditOut] = []
