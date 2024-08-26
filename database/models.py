from datetime import datetime
from enum import Enum

from sqlalchemy import String, DateTime, Enum as SQLAlchemyEnum, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Role(Enum):
    ADMIN = "admin"
    VENDOR = "vendor"
    CLIENT = "client"


class Base(DeclarativeBase):
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[str] = mapped_column(nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str] = mapped_column(String(255), nullable=True)
    role: Mapped[Role] = mapped_column(SQLAlchemyEnum(Role), nullable=False, default=Role.CLIENT)
    allowed_groups_count: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
