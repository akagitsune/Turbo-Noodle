"""Unit tests for the DataIngester helper methods."""

import pytest
import pandas as pd
from unittest.mock import MagicMock
from src.data.ingest import DataIngester
from datetime import date

@pytest.fixture
def mock_db_connector():
    """Return a MagicMock database connector."""
    return MagicMock()

@pytest.fixture
def ingester(mock_db_connector):
    """Return a DataIngester backed by the mock connector."""
    return DataIngester(mock_db_connector)

def test_safe_parse_json_list(ingester):
    """Verify JSON list parsing handles valid input, bad input, and nulls."""
    # Valid JSON string
    text = '[{"id": 1, "name": "Action"}]'
    result = ingester.safe_parse_json_list(text)
    assert result == [{"id": 1, "name": "Action"}]

    # Invalid JSON string
    assert ingester.safe_parse_json_list("invalid") == []

    # NaN/None
    assert ingester.safe_parse_json_list(None) == []
    assert ingester.safe_parse_json_list(float('nan')) == []

def test_parse_date(ingester):
    """Verify date parsing returns correct date objects or None for bad inputs."""
    assert ingester.parse_date("2010-07-16") == date(2010, 7, 16)
    assert ingester.parse_date("") is None
    assert ingester.parse_date(None) is None
    assert ingester.parse_date("invalid-date") is None

def test_extract_year(ingester):
    """Verify year extraction from date strings and edge cases."""
    assert ingester.extract_year("2010-07-16") == 2010
    assert ingester.extract_year("") is None
    assert ingester.extract_year(None) is None
    assert ingester.extract_year("2010") == 2010

def test_extract_entities_from_movies(ingester):
    """Verify that movie entities (genres, countries, etc.) are correctly extracted from a DataFrame."""
    data = {
        'id': [1],
        'title': ['Inception'],
        'genres': ['[{"id": 28, "name": "Action"}]'],
        'production_countries': ['[{"iso_3166_1": "US", "name": "United States"}]'],
        'spoken_languages': ['[{"iso_639_1": "en", "name": "English"}]'],
        'production_companies': ['[{"id": 923, "name": "Legendary Pictures"}]'],
        'keywords': ['[{"id": 1, "name": "dream"}]'],
        'release_date': ['2010-07-16'],
        'runtime': [148],
        'original_language': ['en']
    }
    df = pd.DataFrame(data)

    movies, genres, countries, languages, companies, keywords = ingester._extract_entities_from_movies(df)

    assert len(movies) == 1
    assert movies[0]['title'] == 'Inception'
    assert 28 in genres
    assert 'US' in countries
    assert 'en' in languages
    assert 923 in companies
    assert 1 in keywords

def test_extract_credits_data(ingester):
    """Verify that cast and crew data are correctly extracted and de-duplicated."""
    data = {
        'movie_id': [1],
        'cast': ['[{"id": 6193, "name": "Leonardo DiCaprio", "character": "Cobb", "order": 0}]'],
        'crew': ['[{"id": 525, "name": "Christopher Nolan", "job": "Director", "department": "Directing"}]']
    }
    df = pd.DataFrame(data)

    actors, directors, crew_members, movie_actors, movie_directors, movie_crew = ingester._extract_credits_data(df)

    assert 6193 in actors
    assert 525 in directors
    assert 525 in crew_members
    assert len(movie_actors) == 1
    assert movie_actors[0]['actor_id'] == 6193
    assert len(movie_directors) == 1
    assert movie_directors[0]['director_id'] == 525
