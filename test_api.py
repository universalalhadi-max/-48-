"""
اختبارات شاملة لواجهة برمجة التطبيقات (API)، تُشغَّل مقابل قاعدة بيانات PostgreSQL حقيقية
(وليس محاكاة)، لضمان أن كل شيء يعمل فعلياً كما سيعمل بعد النشر.

التشغيل:  DATABASE_URL=postgresql://postgres:testpass123@localhost:5432/souq48_test pytest test_api.py -v
"""
import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:testpass123@localhost:5432/souq48_test")

from app.database import Base, engine, SessionLocal
from app import models
from app.auth import hash_password
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_db():
    """يُعيد إنشاء الجداول فارغة قبل كل اختبار، حتى لا تتأثر الاختبارات ببعضها."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    admin = models.User(phone="777162770", name="مشرف السوق", password_hash=hash_password("1234"), role="admin", protected=True)
    collector = models.User(phone="772777009", name="محمد الجعدبي", password_hash=hash_password("1234"), role="collector")
    tenant = models.Tenant(id="t1", shop="أ-1", name="حكيم وهشام", phone="967774660644", rent=0)
    db.add_all([admin, collector, tenant])
    db.commit()
    db.close()
    yield


def admin_token():
    r = client.post("/auth/login", json={"phone": "777162770", "password": "1234"})
    assert r.status_code == 200
    return r.json()["token"]


def collector_token(device_id="device-A"):
    r = client.post("/auth/login", json={"phone": "772777009", "password": "1234", "device_id": device_id})
    assert r.status_code == 200
    return r.json()["token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- تسجيل الدخول ----------
def test_health_check():
    r = client.get("/api/health")
    assert r.status_code == 200


def test_root_serves_frontend_html():
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "سوق 48" in r.text


def test_manifest_and_sw_served():
    m = client.get("/manifest.json")
    assert m.status_code == 200
    sw = client.get("/sw.js")
    assert sw.status_code == 200


def test_icon_served():
    r = client.get("/icons/icon-192.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"


def test_login_wrong_phone_rejected():
    r = client.post("/auth/login", json={"phone": "000000000", "password": "1234"})
    assert r.status_code == 401


def test_login_wrong_password_rejected():
    r = client.post("/auth/login", json={"phone": "777162770", "password": "wrong"})
    assert r.status_code == 401


def test_admin_login_succeeds_without_device_id():
    r = client.post("/auth/login", json={"phone": "777162770", "password": "1234"})
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


def test_collector_login_requires_device_id():
    r = client.post("/auth/login", json={"phone": "772777009", "password": "1234"})
    assert r.status_code == 400


# ---------- ربط الجهاز (الميزة الأهم) ----------
def test_collector_first_login_claims_device():
    r = client.post("/auth/login", json={"phone": "772777009", "password": "1234", "device_id": "device-A"})
    assert r.status_code == 200


def test_collector_second_login_same_device_succeeds():
    client.post("/auth/login", json={"phone": "772777009", "password": "1234", "device_id": "device-A"})
    r = client.post("/auth/login", json={"phone": "772777009", "password": "1234", "device_id": "device-A"})
    assert r.status_code == 200


def test_collector_login_from_different_device_rejected():
    client.post("/auth/login", json={"phone": "772777009", "password": "1234", "device_id": "device-A"})
    r = client.post("/auth/login", json={"phone": "772777009", "password": "1234", "device_id": "device-B"})
    assert r.status_code == 403


def test_admin_can_reset_device_binding():
    client.post("/auth/login", json={"phone": "772777009", "password": "1234", "device_id": "device-A"})
    # قبل إعادة التعيين: جهاز آخر مرفوض
    blocked = client.post("/auth/login", json={"phone": "772777009", "password": "1234", "device_id": "device-B"})
    assert blocked.status_code == 403

    admin_h = auth_headers(admin_token())
    users = client.get("/users", headers=admin_h).json()
    collector_id = next(u["id"] for u in users if u["phone"] == "772777009")
    reset = client.post(f"/users/{collector_id}/reset-device", headers=admin_h)
    assert reset.status_code == 200
    assert reset.json()["device_bound"] is False

    # بعد إعادة التعيين: جهاز جديد يُقبل الآن
    allowed = client.post("/auth/login", json={"phone": "772777009", "password": "1234", "device_id": "device-B"})
    assert allowed.status_code == 200


# ---------- تغيير كلمة المرور ----------
def test_change_password_wrong_current_rejected():
    h = auth_headers(admin_token())
    r = client.post("/auth/change-password", json={"current_password": "wrong", "new_password": "newpass1"}, headers=h)
    assert r.status_code == 401


def test_change_password_then_login_with_new_password():
    h = auth_headers(admin_token())
    r = client.post("/auth/change-password", json={"current_password": "1234", "new_password": "newpass1"}, headers=h)
    assert r.status_code == 204
    old = client.post("/auth/login", json={"phone": "777162770", "password": "1234"})
    assert old.status_code == 401
    new = client.post("/auth/login", json={"phone": "777162770", "password": "newpass1"})
    assert new.status_code == 200


# ---------- صلاحيات الأدوار ----------
def test_collector_cannot_create_tenant():
    h = auth_headers(collector_token())
    r = client.post("/tenants", json={"shop": "ب-1", "name": "تجربة"}, headers=h)
    assert r.status_code == 403


def test_collector_can_list_tenants():
    h = auth_headers(collector_token())
    r = client.get("/tenants", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_unauthenticated_request_rejected():
    r = client.get("/tenants")
    assert r.status_code == 401


# ---------- المستأجرون ----------
def test_admin_create_edit_delete_tenant():
    h = auth_headers(admin_token())
    created = client.post("/tenants", json={"shop": "ب-1", "name": "مستأجر جديد", "rent": 15000}, headers=h)
    assert created.status_code == 201
    tid = created.json()["id"]

    edited = client.patch(f"/tenants/{tid}", json={"name": "اسم معدّل"}, headers=h)
    assert edited.status_code == 200
    assert edited.json()["name"] == "اسم معدّل"

    deleted = client.delete(f"/tenants/{tid}", headers=h)
    assert deleted.status_code == 204
    listing = client.get("/tenants", headers=h).json()
    assert all(t["id"] != tid for t in listing)


# ---------- التحصيل: الدفع (push) من الجهاز، متكرر بأمان ----------
def test_push_record_and_idempotent_retry():
    h = auth_headers(collector_token())
    payload = {
        "id": "rec-1", "tenant_id": "t1", "tenant_name": "حكيم وهشام", "shop": "أ-1",
        "amount": 15000, "date": "2026-09-03T10:00:00Z", "collector_name": "محمد الجعدبي", "collector_phone": "772777009",
    }
    first = client.post("/records", json=payload, headers=h)
    assert first.status_code == 201

    # إعادة إرسال نفس السجل (محاكاة انقطاع شبكة وإعادة محاولة) يجب ألا تُنشئ نسخة مكررة
    retry = client.post("/records", json=payload, headers=h)
    assert retry.status_code == 201
    sync = client.get("/sync", headers=h).json()
    assert len(sync["records"]) == 1


def test_push_record_for_unknown_tenant_rejected():
    h = auth_headers(collector_token())
    payload = {
        "id": "rec-x", "tenant_id": "no-such-tenant", "tenant_name": "؟", "shop": "؟",
        "amount": 100, "date": "2026-09-03T10:00:00Z",
    }
    r = client.post("/records", json=payload, headers=h)
    assert r.status_code == 404


# ---------- تعديل/حذف تحصيل + سجل المراجعة ----------
def test_edit_record_requires_reason_and_logs_audit():
    h = auth_headers(admin_token())
    client.post("/records", json={
        "id": "rec-2", "tenant_id": "t1", "tenant_name": "حكيم وهشام", "shop": "أ-1",
        "amount": 10000, "date": "2026-09-03T10:00:00Z",
    }, headers=h)

    no_reason = client.patch("/records/rec-2", json={"amount": 12000, "date": "2026-09-03T10:00:00Z", "reason": ""}, headers=h)
    assert no_reason.status_code == 400

    ok = client.patch("/records/rec-2", json={"amount": 12000, "date": "2026-09-03T10:00:00Z", "reason": "تصحيح خطأ"}, headers=h)
    assert ok.status_code == 200
    assert float(ok.json()["amount"]) == 12000

    audit = client.get("/audit", headers=h).json()
    assert len(audit) == 1 and audit[0]["action"] == "edit"


def test_collector_cannot_edit_record():
    admin_h = auth_headers(admin_token())
    client.post("/records", json={
        "id": "rec-3", "tenant_id": "t1", "tenant_name": "حكيم وهشام", "shop": "أ-1",
        "amount": 5000, "date": "2026-09-03T10:00:00Z",
    }, headers=admin_h)

    collector_h = auth_headers(collector_token())
    r = client.patch("/records/rec-3", json={"amount": 1, "date": "2026-09-03T10:00:00Z", "reason": "x"}, headers=collector_h)
    assert r.status_code == 403


def test_delete_record_requires_reason_and_logs_audit():
    h = auth_headers(admin_token())
    client.post("/records", json={
        "id": "rec-4", "tenant_id": "t1", "tenant_name": "حكيم وهشام", "shop": "أ-1",
        "amount": 7000, "date": "2026-09-03T10:00:00Z",
    }, headers=h)

    no_reason = client.post("/records/rec-4/delete", json={"reason": ""}, headers=h)
    assert no_reason.status_code == 400

    ok = client.post("/records/rec-4/delete", json={"reason": "قيد مكرر"}, headers=h)
    assert ok.status_code == 204

    sync = client.get("/sync", headers=h).json()
    assert len(sync["records"]) == 0
    audit = client.get("/audit", headers=h).json()
    assert any(a["action"] == "delete" for a in audit)


# ---------- المزامنة التزايدية (since) ----------
def test_sync_since_only_returns_changes_after_watermark():
    h = auth_headers(admin_token())
    first_sync = client.get("/sync", headers=h).json()
    watermark = first_sync["server_time"]

    client.post("/records", json={
        "id": "rec-5", "tenant_id": "t1", "tenant_name": "حكيم وهشام", "shop": "أ-1",
        "amount": 3000, "date": "2026-09-03T10:00:00Z",
    }, headers=h)

    second_sync = client.get("/sync", params={"since": watermark}, headers=h).json()
    assert len(second_sync["records"]) == 1
    assert second_sync["records"][0]["id"] == "rec-5"


# ---------- إدارة المستخدمين ----------
def test_duplicate_phone_rejected():
    h = auth_headers(admin_token())
    client.post("/users", json={"phone": "733333333", "name": "أ", "password": "x", "role": "collector"}, headers=h)
    dup = client.post("/users", json={"phone": "733333333", "name": "ب", "password": "y", "role": "collector"}, headers=h)
    assert dup.status_code == 409


def test_protected_admin_cannot_be_deleted():
    h = auth_headers(admin_token())
    users = client.get("/users", headers=h).json()
    root_id = next(u["id"] for u in users if u["protected"])
    r = client.delete(f"/users/{root_id}", headers=h)
    assert r.status_code == 400


def test_logout_invalidates_token():
    token = admin_token()
    h = auth_headers(token)
    client.post("/auth/logout", headers=h)
    r = client.get("/tenants", headers=h)
    assert r.status_code == 401
