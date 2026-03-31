import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator
from langchain_community.utilities import SQLDatabase

load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseConnector:
    """
    Manages database connections and sessions using SQLAlchemy.
    Provides engine, session factory, and context manager for sessions.
    """

    def __init__(self, database_url: str | None = None):
        """Initialise connector with an optional database URL.

        Falls back to the DATABASE_URL environment variable, then to a local SQLite file.
        """
        self.database_url = database_url or os.getenv("DATABASE_URL", "sqlite:///./movies.db")
        self._engine = None
        self._session_factory = None
        self._sql_db = None
        self._base = declarative_base()

    @property
    def engine(self):
        """Lazy-loaded SQLAlchemy engine."""
        if self._engine is None:
            logger.info("Creating database engine for %s", self.database_url)
            connect_args = (
                {"check_same_thread": False}
                if self.database_url.startswith("sqlite")
                else {}
            )
            self._engine = create_engine(self.database_url, connect_args=connect_args)
        return self._engine

    @property
    def session_factory(self):
        """Lazy-loaded session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine
            )
        return self._session_factory

    @property
    def sql_db(self) -> SQLDatabase:
        """Lazy-loaded LangChain SQLDatabase."""
        if self._sql_db is None:
            logger.info("Creating LangChain SQLDatabase for %s", self.database_url)
            self._sql_db = SQLDatabase.from_uri(self.database_url)
        return self._sql_db

    @property
    def base(self):
        """Returns the declarative base for model definitions."""
        return self._base

    def get_session(self) -> Generator[Session, None, None]:
        """
        Generator that yields a database session and ensures proper cleanup.
        Use as a dependency in FastAPI or directly in a context.
        """
        db = self.session_factory()
        try:
            yield db
        finally:
            db.close()

    def get_db(self) -> Session:
        """
        Returns a database session. Caller is responsible for closing.
        """
        return self.session_factory()

    def execute_sql(self, sql: str, params: dict | None = None) -> list[dict]:
        """
        Execute a raw SQL string and return results as a list of dicts.
        Raises any SQLAlchemy exception so callers can handle retries.
        """
        logger.debug("execute_sql: %s | params=%r", sql, params)
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            columns = list(result.keys())
            rows = [
                {col: val for col, val in zip(columns, row)}
                for row in result.fetchall()
            ]
        logger.debug("execute_sql: returned %d row(s)", len(rows))
        return rows


# Global instance for application-wide use
db_connector = DatabaseConnector()

# Backwards-compatible exports
Base = db_connector.base
engine = db_connector.engine
SessionLocal = db_connector.session_factory


def get_db():
    """Backwards-compatible dependency function for FastAPI."""
    yield from db_connector.get_session()
