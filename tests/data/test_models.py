"""Tests for SQLAlchemy ORM model instantiation."""

from src.data import models
from datetime import date

def test_movie_model_instantiation():
    """Verify that a Movie ORM object stores its attributes correctly."""
    movie = models.Movie(
        title="Inception",
        tmdb_id=27205,
        release_date=date(2010, 7, 16),
        year=2010,
        runtime=148.0,
        vote_average=8.3
    )
    assert movie.title == "Inception"
    assert movie.tmdb_id == 27205
    assert movie.year == 2010
    assert movie.runtime == 148.0

def test_genre_model_instantiation():
    """Verify that a Genre ORM object stores its attributes correctly."""
    genre = models.Genre(tmdb_id=28, name="Action")
    assert genre.tmdb_id == 28
    assert genre.name == "Action"

def test_actor_model_instantiation():
    """Verify that an Actor ORM object stores its attributes correctly."""
    actor = models.Actor(tmdb_id=6193, name="Leonardo DiCaprio")
    assert actor.tmdb_id == 6193
    assert actor.name == "Leonardo DiCaprio"

def test_director_model_instantiation():
    """Verify that a Director ORM object stores its attributes correctly."""
    director = models.Director(tmdb_id=525, name="Christopher Nolan")
    assert director.tmdb_id == 525
    assert director.name == "Christopher Nolan"
