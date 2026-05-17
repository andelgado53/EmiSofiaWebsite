from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_now, onupdate=_now
    )

    # Relationships
    note_labels: Mapped[list["NoteLabel"]] = relationship(
        "NoteLabel", back_populates="note", cascade="all, delete-orphan"
    )
    photos: Mapped[list["Photo"]] = relationship(
        "Photo", back_populates="note", cascade="all, delete-orphan"
    )

    @property
    def labels(self) -> list["Label"]:
        return [nl.label for nl in self.note_labels]


class Label(Base):
    __tablename__ = "labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # String column with NOCASE collation for case-insensitive uniqueness in SQLite
    name: Mapped[str] = mapped_column(
        String(50).with_variant(String(50, collation="NOCASE"), "sqlite"),
        nullable=False,
        unique=True,
    )

    # Relationships
    note_labels: Mapped[list["NoteLabel"]] = relationship(
        "NoteLabel", back_populates="label"
    )


class NoteLabel(Base):
    __tablename__ = "note_labels"

    note_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("notes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    label_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("labels.id"),
        primary_key=True,
    )

    # Relationships
    note: Mapped["Note"] = relationship("Note", back_populates="note_labels")
    label: Mapped["Label"] = relationship("Label", back_populates="note_labels")


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    note_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
    )
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False)
    cdn_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_now
    )

    # Relationships
    note: Mapped["Note"] = relationship("Note", back_populates="photos")
