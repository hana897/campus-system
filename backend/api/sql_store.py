"""SQLAlchemy persistence for application data not represented by Django models.

The engine is built from Django's active database configuration so these tables
live beside existing accounts/assets/verification data. Existing tables and rows
are never migrated or dropped by this module.
"""
from datetime import datetime, timezone

from django.conf import settings
from sqlalchemy import Boolean, DateTime, Integer, JSON, LargeBinary, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool


def _database_url():
    config = settings.DATABASES["default"]
    name = config["NAME"]
    if config["ENGINE"].endswith("sqlite3"):
        return "sqlite+pysqlite:///" + str(name).replace("\\", "/")
    if config["ENGINE"].endswith("postgresql"):
        user = config.get("USER", "")
        password = config.get("PASSWORD", "")
        host = config.get("HOST", "127.0.0.1")
        port = config.get("PORT", "5432")
        auth = user + (":" + password if password else "")
        return f"postgresql+psycopg://{auth}@{host}:{port}/{name}"
    raise RuntimeError(f"Unsupported database engine: {config['ENGINE']}")


_url = _database_url()
_engine_options = {"pool_pre_ping": True}
if _url.startswith("postgresql+"):
    _engine_options["connect_args"] = {"connect_timeout": 5}
if _url.endswith(":memory:"):
    _engine_options.update(poolclass=StaticPool, connect_args={"check_same_thread": False})
engine = create_engine(_url, **_engine_options)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class IncidentRecord(Base):
    __tablename__ = "scsams_incidents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    asset_id: Mapped[str] = mapped_column(String(64), default="")
    asset_name: Mapped[str] = mapped_column(String(200), default="")
    owner_name: Mapped[str] = mapped_column(String(200), default="")
    university_id: Mapped[str] = mapped_column(String(64), default="")
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    gate: Mapped[str] = mapped_column(String(120), default="Main Gate")
    reporting_officer: Mapped[str] = mapped_column(String(200), default="")
    severity: Mapped[str] = mapped_column(String(20), default="LOW")
    status: Mapped[str] = mapped_column(String(24), default="OPEN")
    description: Mapped[str] = mapped_column(Text, default="")
    assigned_investigator: Mapped[str] = mapped_column(String(200), default="")
    resolution_notes: Mapped[str] = mapped_column(Text, default="")
    created_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)


class UserSettingsRecord(Base):
    __tablename__ = "scsams_user_settings"
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class NotificationRecord(Base):
    __tablename__ = "scsams_notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[str] = mapped_column(String(20), default="info")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    link: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class GateRecord(Base):
    __tablename__ = "scsams_gates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    status: Mapped[str] = mapped_column(String(24), default="OPERATIONAL")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class StoredFile(Base):
    __tablename__ = "scsams_stored_files"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(120))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class MediaFileRecord(Base):
    """Uploaded Django media (asset images, QR codes, documents) kept in the database."""
    __tablename__ = "scsams_media_files"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    mime_type: Mapped[str] = mapped_column(String(120))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


def ensure_tables():
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        if not session.scalar(select(GateRecord.id).limit(1)):
            session.add_all([GateRecord(name=name) for name in ("Main Gate", "North Gate", "Library Gate", "Hostel Exit", "Engineering Gate")])
            session.commit()
