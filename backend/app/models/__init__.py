from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    poster_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    vote_average: Mapped[float | None] = mapped_column(Float, nullable=True)
    genres: Mapped[str | None] = mapped_column(String(512), nullable=True)  # JSON-encoded list of genre names
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    credits: Mapped[list["Credit"]] = relationship(back_populates="movie", lazy="raise")
    watch_events: Mapped[list["WatchEvent"]] = relationship(back_populates="movie", lazy="raise")


class Actor(Base):
    __tablename__ = "actors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    credits: Mapped[list["Credit"]] = relationship(back_populates="actor", lazy="raise")


class Credit(Base):
    __tablename__ = "credits"
    __table_args__ = (UniqueConstraint("movie_id", "actor_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False, index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("actors.id"), nullable=False, index=True)
    character: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order: Mapped[int | None] = mapped_column(Integer, nullable=True)

    movie: Mapped["Movie"] = relationship(back_populates="credits", lazy="raise")
    actor: Mapped["Actor"] = relationship(back_populates="credits", lazy="raise")


class WatchEvent(Base):
    __tablename__ = "watch_events"
    __table_args__ = (UniqueConstraint("tmdb_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    movie_id: Mapped[int | None] = mapped_column(ForeignKey("movies.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # plex_sync | plex_webhook | manual
    watched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    movie: Mapped["Movie | None"] = relationship(back_populates="watch_events", lazy="raise")
