from datetime import datetime
from enum import Enum

from sqlalchemy import String, DateTime, Enum as SQLAlchemyEnum, Integer, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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
    groups: Mapped[list["Group"]] = relationship("Group", back_populates="user")


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[str] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="groups")
    city_id: Mapped[int] = mapped_column(nullable=False)
    subject_id: Mapped[int] = mapped_column(nullable=False)
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="group", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    group: Mapped["Group"] = relationship("Group", back_populates="messages")
