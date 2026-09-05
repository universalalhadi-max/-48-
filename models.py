"""
نماذج قاعدة البيانات (الجداول).

ملاحظة تصميم مهمة: معرّفات المستأجرين وعمليات التحصيل (id) نوعها نص (String) وليست أرقاماً
تلقائية، لأن التطبيق يُنشئ هذه المعرّفات في الجهاز نفسه (حتى أثناء عدم الاتصال بالإنترنت)، ثم
يرسلها لاحقاً للخادم عند توفر الاتصال. لو كانت المعرّفات أرقاماً تلقائية من قاعدة البيانات، لتعارضت
معرّفات أُنشئت على أجهزة مختلفة وهي غير متصلة. النص الفريد الذي يُنشئه كل جهاز يحل هذه المشكلة ببساطة.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base


def now_utc():
    return datetime.now(timezone.utc)


def new_id():
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=new_id)
    phone = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="collector")  # 'admin' | 'collector'
    protected = Column(Boolean, nullable=False, default=False)  # الحساب الأساسي، لا يُحذف ولا يُقيَّد بجهاز
    device_id = Column(String, nullable=True)  # الجهاز المُرتبط بالحساب (للمحصّلين فقط) — NULL يعني غير مرتبط بعد
    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class Session(Base):
    __tablename__ = "sessions"

    token = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex + uuid.uuid4().hex)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    user = relationship("User")


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=new_id)
    shop = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False, default="")
    phone = Column(String, nullable=True)
    rent = Column(Numeric(12, 2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class Record(Base):
    __tablename__ = "records"

    id = Column(String, primary_key=True)  # يُنشأ في الجهاز (client-generated) وليس هنا
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    tenant_name = Column(String, nullable=False)  # لقطة من اسم المستأجر وقت التحصيل
    shop = Column(String, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)  # وقت التحصيل الفعلي
    collector_name = Column(String, nullable=True)
    collector_phone = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)  # وقت وصول السجل للخادم (لأغراض المزامنة)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String, primary_key=True, default=new_id)
    at = Column(DateTime(timezone=True), default=now_utc)
    by_name = Column(String, nullable=True)
    by_phone = Column(String, nullable=True)
    action = Column(String, nullable=False)  # 'edit' | 'delete'
    record_id = Column(String, nullable=False)
    tenant_name = Column(String, nullable=True)
    shop = Column(String, nullable=True)
    old_amount = Column(Numeric(12, 2), nullable=True)
    new_amount = Column(Numeric(12, 2), nullable=True)
    old_date = Column(DateTime(timezone=True), nullable=True)
    new_date = Column(DateTime(timezone=True), nullable=True)
    reason = Column(Text, nullable=False)
