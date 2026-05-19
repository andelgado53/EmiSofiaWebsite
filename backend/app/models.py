from datetime import date, datetime, timezone

from sqlalchemy import (
    Date,
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


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    trip_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_now, onupdate=_now
    )

    # Relationships
    photos: Mapped[list["TripPhoto"]] = relationship(
        "TripPhoto", back_populates="trip", cascade="all, delete-orphan"
    )


class TripPhoto(Base):
    __tablename__ = "trip_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False)
    cdn_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    media_type: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="photo"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_now
    )

    # Relationships
    trip: Mapped["Trip"] = relationship("Trip", back_populates="photos")


class Moment(Base):
    __tablename__ = "moments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    moment_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_now, onupdate=_now
    )

    # Relationships
    photos: Mapped[list["MomentPhoto"]] = relationship(
        "MomentPhoto", back_populates="moment", cascade="all, delete-orphan"
    )


class MomentPhoto(Base):
    __tablename__ = "moment_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    moment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("moments.id", ondelete="CASCADE"),
        nullable=False,
    )
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False)
    cdn_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    media_type: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="photo"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_now
    )

    # Relationships
    moment: Mapped["Moment"] = relationship("Moment", back_populates="photos")


class ArtPiece(Base):
    __tablename__ = "art_pieces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False)
    cdn_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    media_type: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="photo"
    )
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_now, onupdate=_now
    )
