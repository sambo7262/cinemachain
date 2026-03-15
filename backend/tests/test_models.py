"""Tests for ORM model definitions — verifies all four models register
correctly with Base.metadata and have the expected constraints."""
import pytest


def test_all_four_tables_registered():
    """All four models must register with Base.metadata."""
    from app.models import Base, Movie, Actor, Credit, WatchEvent
    tables = set(Base.metadata.tables.keys())
    assert tables == {"movies", "actors", "credits", "watch_events"}, (
        f"Expected 4 tables, got: {tables}"
    )


def test_movie_lazy_raise():
    from app.models import Movie
    assert Movie.credits.property.lazy == "raise"
    assert Movie.watch_events.property.lazy == "raise"


def test_actor_lazy_raise():
    from app.models import Actor
    assert Actor.credits.property.lazy == "raise"


def test_credit_lazy_raise():
    from app.models import Credit
    assert Credit.movie.property.lazy == "raise"
    assert Credit.actor.property.lazy == "raise"


def test_watch_event_lazy_raise():
    from app.models import WatchEvent
    assert WatchEvent.movie.property.lazy == "raise"


def test_credit_unique_constraint():
    from app.models import Credit
    from sqlalchemy import UniqueConstraint
    constraints = Credit.__table_args__
    unique_cols = None
    for c in constraints:
        if isinstance(c, UniqueConstraint):
            unique_cols = {col.key for col in c.columns}
    assert unique_cols == {"movie_id", "actor_id"}, (
        f"Credit must have unique(movie_id, actor_id), got: {unique_cols}"
    )


def test_watch_event_unique_tmdb_id():
    from app.models import WatchEvent
    from sqlalchemy import UniqueConstraint
    constraints = WatchEvent.__table_args__
    found = False
    for c in constraints:
        if isinstance(c, UniqueConstraint):
            cols = {col.key for col in c.columns}
            if "tmdb_id" in cols:
                found = True
    assert found, "WatchEvent must have unique constraint on tmdb_id"


def test_plexapi_in_requirements():
    import pathlib
    req_path = pathlib.Path(__file__).parent.parent / "requirements.txt"
    content = req_path.read_text()
    assert "plexapi==4.18.0" in content, f"plexapi==4.18.0 not found in requirements.txt"
