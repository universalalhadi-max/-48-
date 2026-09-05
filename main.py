"""
نقطة تشغيل خادم سوق 48.

يخدم هذا الملف شيئين معاً من نفس الخادم: تطبيق الهاتف (ملفات static/) وواجهة برمجة
التطبيقات (API). هذا يعني أنك لا تحتاج أي استضافة منفصلة لتطبيق الهاتف — رابط واحد
لكل شيء، ومستودع GitHub يمكن أن يبقى خاصاً (Render لا يشترط أن يكون عاماً كما تشترط
استضافة GitHub Pages المجانية).

للتجربة المحلية:  uvicorn app.main:app --reload
للنشر الفعلي: راجع README.md.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import Base, engine
from .routers import auth, users, tenants, records, audit

# ينشئ الجداول تلقائياً إن لم تكن موجودة (لا يحذف أو يعدّل جدولاً موجوداً بالفعل)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="سوق 48", version="1.1")

# مفتوح لأي مصدر حالياً لتبسيط الأمور أثناء الإعداد؛ بما أن التطبيق والـ API يُخدَّمان الآن
# من نفس الخادم (نفس النطاق)، لا حاجة فعلية لهذا التوسّع، لكن إبقاؤه لا يشكّل خطراً إضافياً
# لأن كل نقطة نهاية حساسة محمية بتسجيل دخول مسبق على أي حال.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tenants.router)
app.include_router(records.router)
app.include_router(audit.router)

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

app.mount("/icons", StaticFiles(directory=os.path.join(STATIC_DIR, "icons")), name="icons")


@app.get("/manifest.json")
def manifest():
    return FileResponse(os.path.join(STATIC_DIR, "manifest.json"), media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    return FileResponse(os.path.join(STATIC_DIR, "sw.js"), media_type="application/javascript")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "souq48-api"}


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
