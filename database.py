"""
إعداد الاتصال بقاعدة البيانات.
يقرأ رابط الاتصال من متغير البيئة DATABASE_URL (تضبطه شركة الاستضافة تلقائياً غالباً).
في حال عدم وجوده، يستخدم قاعدة بيانات SQLite محلية باسم dev.db — مفيد فقط للتجربة السريعة على جهازك،
غير مناسب للاستخدام الفعلي (لهذا نوصي بـ PostgreSQL في الإنتاج، كما هو موضح في README).
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")

# بعض مزوّدي الاستضافة (مثل Render) يعطون رابطاً يبدأ بـ postgres:// بدل postgresql://
# وهي صيغة قديمة لا تقبلها SQLAlchemy الحديثة، فنصححها تلقائياً هنا.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
