from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .contracts import now, uid


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)


class Memory(Base):
    __tablename__ = "memories"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(20))
    scope: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(200))
    confidence: Mapped[float]
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    expires_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default="planned")
    steps: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    tool: Mapped[str] = mapped_column(String(100))
    arguments: Mapped[dict] = mapped_column(JSON)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    step_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)


class Execution(Base):
    __tablename__ = "executions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    tool: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30))
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)


class Audit(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)


class Store:
    def __init__(self, url: str):
        if url.startswith("sqlite:///") and ":memory:" not in url:
            Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        kw = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, **kw)
        if url.startswith("sqlite"):

            @event.listens_for(self.engine, "connect")
            def configure(conn, record):
                conn.execute("PRAGMA foreign_keys=ON")
                conn.execute("PRAGMA busy_timeout=5000")

        self.factory = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def db(self):
        with self.factory.begin() as db:
            yield db


def record(obj):
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}
