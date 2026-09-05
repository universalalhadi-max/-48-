"""
سكربت التهيئة الأولى — شغّله مرة واحدة فقط بعد أول نشر للخادم:

    python3 seed.py

يقوم بـ:
1. إنشاء حساب المشرف الأساسي (نفس رقمك الحالي 777162770) بكلمة مرور مؤقتة يجب تغييرها فوراً.
2. استيراد قائمة المستأجرين الـ 75 الحالية (من tenants_seed_data.json المرفق) — حتى لا تبدأ فارغاً.

آمن التشغيل أكثر من مرة: لن يُنشئ حساب المشرف مرتين، ولن يستورد نفس المستأجرين مرتين
(يتحقق من رقم المحل قبل الإضافة).
"""
import json
import os
from app.database import SessionLocal, Base, engine
from app import models
from app.auth import hash_password

ADMIN_PHONE = "777162770"
TEMP_PASSWORD = "1234"  # يجب تغييرها فور أول دخول من زر 🔑 في التطبيق


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.query(models.User).filter(models.User.phone == ADMIN_PHONE).first()
        if admin is None:
            admin = models.User(
                phone=ADMIN_PHONE, name="مشرف السوق",
                password_hash=hash_password(TEMP_PASSWORD),
                role="admin", protected=True,
            )
            db.add(admin)
            db.commit()
            print(f"✔ تم إنشاء حساب المشرف {ADMIN_PHONE} — كلمة المرور المؤقتة: {TEMP_PASSWORD} (غيّرها فوراً)")
        else:
            print(f"– حساب المشرف {ADMIN_PHONE} موجود مسبقاً، لم يتم إنشاؤه من جديد")

        seed_path = os.path.join(os.path.dirname(__file__), "tenants_seed_data.json")
        if os.path.exists(seed_path):
            with open(seed_path, "r", encoding="utf-8") as f:
                tenants_data = json.load(f)
            added = 0
            for t in tenants_data:
                exists = db.query(models.Tenant).filter(models.Tenant.shop == t["shop"]).first()
                if exists is None:
                    db.add(models.Tenant(shop=t["shop"], name=t.get("name", ""), phone=t.get("phone"), rent=t.get("rent", 0)))
                    added += 1
            db.commit()
            print(f"✔ تم استيراد {added} مستأجر جديد من tenants_seed_data.json ({len(tenants_data)} في الملف إجمالاً)")
        else:
            print("– لم يُعثر على tenants_seed_data.json، تم تخطي استيراد المستأجرين")
    finally:
        db.close()


if __name__ == "__main__":
    main()
