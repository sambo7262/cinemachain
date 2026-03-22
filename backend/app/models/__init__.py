from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional
import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    poster_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    vote_average: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    genres: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # JSON-encoded list of genre names
    runtime: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vote_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mpaa_rating: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    overview: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    poster_local_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rt_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rt_audience_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    credits: Mapped[list[Credit]] = relationship(back_populates="movie", lazy="raise")
    watch_events: Mapped[list[WatchEvent]] = relationship(back_populates="movie", lazy="raise")


class Actor(Base):
    __tablename__ = "actors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    credits: Mapped[list[Credit]] = relationship(back_populates="actor", lazy="raise")


class Credit(Base):
    __tablename__ = "credits"
    __table_args__ = (UniqueConstraint("movie_id", "actor_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False, index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("actors.id"), nullable=False, index=True)
    character: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    movie: Mapped[Movie] = relationship(back_populates="credits", lazy="raise")
    actor: Mapped[Actor] = relationship(back_populates="credits", lazy="raise")


class WatchEvent(Base):
    __tablename__ = "watch_events"
    __table_args__ = (UniqueConstraint("tmdb_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    movie_id: Mapped[Optional[int]] = mapped_column(ForeignKey("movies.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # plex_sync | plex_webhook | manual
    watched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    movie: Mapped[Optional[Movie]] = relationship(back_populates="watch_events", lazy="raise")


class SessionStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    awaiting_continue = "awaiting_continue"
    ended = "ended"
    archived = "archived"


class GameSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    current_movie_tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    current_movie_watched: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    steps: Mapped[list[GameSessionStep]] = relationship(
        back_populates="session", lazy="raise", order_by="GameSessionStep.step_order"
    )


class GameSessionStep(Base):
    __tablename__ = "game_session_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id"), nullable=False, index=True)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    movie_tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_tmdb_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    movie_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped[GameSession] = relationship(back_populates="steps", lazy="raise")


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
