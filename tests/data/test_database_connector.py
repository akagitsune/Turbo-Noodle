import pytest
from sqlalchemy import text, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.data.database import DatabaseConnector, db_connector
from src.data import models


class TestDatabaseConnector:
    """Tests for the DatabaseConnector class."""

    def test_init_default_url(self):
        """Test initialization with default database URL."""
        connector = DatabaseConnector()
        assert connector.database_url == "sqlite:///./movies.db"

    def test_init_custom_url(self):
        """Test initialization with custom database URL."""
        custom_url = "sqlite:///./test.db"
        connector = DatabaseConnector(database_url=custom_url)
        assert connector.database_url == custom_url

    def test_init_from_env(self, monkeypatch):
        """Test initialization from environment variable."""
        env_url = "sqlite:///./env_test.db"
        monkeypatch.setenv("DATABASE_URL", env_url)
        # Create new connector to pick up env var
        connector = DatabaseConnector()
        assert connector.database_url == env_url

    def test_engine_lazy_load(self):
        """Test that engine is created lazily."""
        connector = DatabaseConnector(database_url="sqlite:///:memory:")
        assert connector._engine is None
        engine = connector.engine
        assert connector._engine is not None
        assert engine is connector.engine  # Should return same instance

    def test_session_factory_lazy_load(self):
        """Test that session factory is created lazily."""
        connector = DatabaseConnector(database_url="sqlite:///:memory:")
        assert connector._session_factory is None
        session_factory = connector.session_factory
        assert connector._session_factory is not None
        assert session_factory is connector.session_factory

    def test_base_property(self):
        """Test that base returns the declarative base."""
        connector = DatabaseConnector(database_url="sqlite:///:memory:")
        base = connector.base
        assert base is not None
        assert base is connector.base  # Should return same instance

    def test_get_db_session(self):
        """Test getting a database session."""
        connector = DatabaseConnector(database_url="sqlite:///:memory:")
        session = connector.get_db()
        assert isinstance(session, Session)
        session.close()

    def test_get_session_generator(self):
        """Test the get_session generator."""
        connector = DatabaseConnector(database_url="sqlite:///:memory:")
        sessions = list(connector.get_session())
        assert len(sessions) == 1
        assert isinstance(sessions[0], Session)

    def test_session_execution(self):
        """Test executing queries within a session."""
        connector = DatabaseConnector(database_url="sqlite:///:memory:")

        # Create a simple table
        with connector.engine.connect() as conn:
            conn.execute(text("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)"))
            conn.execute(text("INSERT INTO test (name) VALUES ('test')"))
            conn.commit()

        session = connector.get_db()
        result = session.execute(text("SELECT name FROM test WHERE id = 1"))
        row = result.fetchone()
        assert row[0] == "test"
        session.close()


class TestDatabaseConnectorIntegration:
    """Integration tests using actual database operations with isolated test databases."""

    @pytest.fixture
    def fresh_db(self, tmp_path):
        """Create a fresh database for testing using global models."""
        # Create a new isolated database file
        db_path = tmp_path / "test.db"
        database_url = f"sqlite:///{db_path}"

        # Create engine and session factory for this test
        engine = create_engine(database_url, connect_args={"check_same_thread": False})
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Create all tables from the models
        models.Base.metadata.create_all(bind=engine)

        class TestDB:
            """Lightweight test double for DatabaseConnector used in integration fixtures."""

            def __init__(self, engine, session_factory):
                """Store engine and session factory for test use."""
                self.engine = engine
                self.session_factory = session_factory

            def get_db(self):
                """Return a new session from the test session factory."""
                return self.session_factory()

        yield TestDB(engine, SessionLocal)

        # Cleanup
        models.Base.metadata.drop_all(bind=engine)

    def test_create_tables_with_models(self, fresh_db):
        """Test that all model tables are created."""
        with fresh_db.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ))
            tables = [row[0] for row in result]

        # Check that all model tables exist
        assert "movies" in tables
        assert "genres" in tables
        assert "actors" in tables
        assert "directors" in tables
        assert "countries" in tables
        assert "languages" in tables
        assert "crew" in tables
        assert "companies" in tables
        assert "keywords" in tables
        assert "movie_genre" in tables
        assert "movie_actor" in tables
        assert "movie_director" in tables

    def test_insert_and_query_movie(self, fresh_db):
        """Test inserting and querying a movie."""
        session = fresh_db.get_db()

        # Create a test movie
        movie = models.Movie(
            tmdb_id=1,
            title="Test Movie",
            year=2024,
            overview="A test movie",
            original_language_code="en"
        )
        session.add(movie)
        session.commit()

        # Query it back
        result = session.query(models.Movie).filter_by(title="Test Movie").first()
        assert result is not None
        assert result.title == "Test Movie"
        assert result.year == 2024
        assert result.tmdb_id == 1

        session.close()

    def test_genre_association(self, fresh_db):
        """Test movie-genre many-to-many relationship."""
        session = fresh_db.get_db()

        # Create genre
        genre = models.Genre(tmdb_id=1, name="Action")
        session.add(genre)
        session.commit()

        # Create movie with genre
        movie = models.Movie(tmdb_id=1, title="Action Movie", year=2024)
        movie.genres.append(genre)
        session.add(movie)
        session.commit()

        # Query movie's genres
        result = session.query(models.Movie).filter_by(title="Action Movie").first()
        assert len(result.genres) == 1
        assert result.genres[0].name == "Action"

        session.close()

    def test_actor_association(self, fresh_db):
        """Test movie-actor many-to-many relationship."""
        session = fresh_db.get_db()

        # Create actor
        actor = models.Actor(tmdb_id=1, name="Tom Hanks")
        session.add(actor)
        session.commit()

        # Create movie with actor
        movie = models.Movie(tmdb_id=1, title="Forrest Gump", year=1994)
        movie.actors.append(actor)
        session.add(movie)
        session.commit()

        # Query movie's actors
        result = session.query(models.Movie).filter_by(title="Forrest Gump").first()
        assert len(result.actors) == 1
        assert result.actors[0].name == "Tom Hanks"

        session.close()

    def test_director_association(self, fresh_db):
        """Test movie-director many-to-many relationship."""
        session = fresh_db.get_db()

        # Create director
        director = models.Director(tmdb_id=1, name="Christopher Nolan")
        session.add(director)
        session.commit()

        # Create movie with director
        movie = models.Movie(tmdb_id=1, title="Inception", year=2010)
        movie.directors.append(director)
        session.add(movie)
        session.commit()

        # Query movie's directors
        result = session.query(models.Movie).filter_by(title="Inception").first()
        assert len(result.directors) == 1
        assert result.directors[0].name == "Christopher Nolan"

        session.close()

    def test_country_association(self, fresh_db):
        """Test movie-country many-to-many relationship."""
        session = fresh_db.get_db()

        # Create country
        country = models.Country(iso_code="US", name="United States")
        session.add(country)
        session.commit()

        # Create movie with country
        movie = models.Movie(tmdb_id=1, title="Hollywood Movie", year=2020)
        movie.countries.append(country)
        session.add(movie)
        session.commit()

        # Query movie's countries
        result = session.query(models.Movie).filter_by(title="Hollywood Movie").first()
        assert len(result.countries) == 1
        assert result.countries[0].iso_code == "US"

        session.close()

    def test_company_association(self, fresh_db):
        """Test movie-company many-to-many relationship."""
        session = fresh_db.get_db()

        # Create company
        company = models.Company(tmdb_id=1, name="Warner Bros")
        session.add(company)
        session.commit()

        # Create movie with company
        movie = models.Movie(tmdb_id=1, title="Blockbuster", year=2020)
        movie.companies.append(company)
        session.add(movie)
        session.commit()

        # Query movie's companies
        result = session.query(models.Movie).filter_by(title="Blockbuster").first()
        assert len(result.companies) == 1
        assert result.companies[0].name == "Warner Bros"

        session.close()


class TestGlobalConnector:
    """Tests for the global db_connector instance."""

    def test_global_connector_exists(self):
        """Test that the global connector exists."""
        assert db_connector is not None
        assert isinstance(db_connector, DatabaseConnector)

    def test_global_connector_singleton(self):
        """Test that the global connector is a singleton."""
        from src.data.database import db_connector as dc2
        assert db_connector is dc2
