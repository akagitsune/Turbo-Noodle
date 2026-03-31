"""SQLAlchemy ORM models for the TMDB movie database."""

from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from src.data.database import Base


# Association Tables
movie_genre_association = Table(
    "movie_genre",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.tmdb_id"), primary_key=True),
    Column("genre_id", Integer, ForeignKey("genres.tmdb_id"), primary_key=True),
)

movie_country_association = Table(
    "movie_country",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.tmdb_id"), primary_key=True),
    Column("country_id", String, ForeignKey("countries.iso_code"), primary_key=True),
)

movie_language_association = Table(
    "movie_language",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.tmdb_id"), primary_key=True),
    Column("language_id", String, ForeignKey("languages.iso_code"), primary_key=True),
)

movie_company_association = Table(
    "movie_company",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.tmdb_id"), primary_key=True),
    Column("company_id", Integer, ForeignKey("companies.tmdb_id"), primary_key=True),
)

movie_keyword_association = Table(
    "movie_keyword",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.tmdb_id"), primary_key=True),
    Column("keyword_id", Integer, ForeignKey("keywords.tmdb_id"), primary_key=True),
)

movie_actor_association = Table(
    "movie_actor",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.tmdb_id"), primary_key=True),
    Column("actor_id", Integer, ForeignKey("actors.tmdb_id"), primary_key=True),
    Column("character_name", String),
    Column("order", Integer),
)

movie_director_association = Table(
    "movie_director",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.tmdb_id"), primary_key=True),
    Column("director_id", Integer, ForeignKey("directors.tmdb_id"), primary_key=True),
)

movie_crew_association = Table(
    "movie_crew",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.tmdb_id"), primary_key=True),
    Column("crew_id", Integer, ForeignKey("crew.tmdb_id"), primary_key=True),
    Column("job", String, primary_key=True),
    Column("department", String),
)


class Movie(Base):
    """ORM model for a TMDB movie entry."""

    __tablename__ = "movies"

    tmdb_id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    original_title = Column(String)
    tagline = Column(Text)
    overview = Column(Text)
    homepage = Column(String)
    status = Column(String)
    release_date = Column(Date)
    year = Column(Integer, index=True)
    runtime = Column(Float)
    original_language_code = Column(String)
    budget = Column(Integer)
    revenue = Column(Integer)
    popularity = Column(Float)
    vote_average = Column(Float)
    vote_count = Column(Integer)

    # Relationships
    genres = relationship("Genre", secondary=movie_genre_association, back_populates="movies")
    countries = relationship("Country", secondary=movie_country_association, back_populates="movies")
    languages = relationship("Language", secondary=movie_language_association, back_populates="movies")
    companies = relationship("Company", secondary=movie_company_association, back_populates="movies")
    keywords = relationship("Keyword", secondary=movie_keyword_association, back_populates="movies")
    actors = relationship("Actor", secondary=movie_actor_association, back_populates="movies")
    directors = relationship("Director", secondary=movie_director_association, back_populates="movies")
    crew = relationship("Crew", secondary=movie_crew_association, back_populates="movies")


class Genre(Base):
    """ORM model for a TMDB genre."""

    __tablename__ = "genres"
    tmdb_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    movies = relationship("Movie", secondary=movie_genre_association, back_populates="genres")


class Country(Base):
    """ORM model for a production country."""

    __tablename__ = "countries"
    iso_code = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    movies = relationship("Movie", secondary=movie_country_association, back_populates="countries")


class Language(Base):
    """ORM model for a spoken language."""

    __tablename__ = "languages"
    iso_code = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    movies = relationship("Movie", secondary=movie_language_association, back_populates="languages")


class Company(Base):
    """ORM model for a production company."""

    __tablename__ = "companies"
    tmdb_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    logo_path = Column(String)
    origin_country = Column(String)
    movies = relationship("Movie", secondary=movie_company_association, back_populates="companies")


class Keyword(Base):
    """ORM model for a TMDB keyword tag."""

    __tablename__ = "keywords"
    tmdb_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    movies = relationship("Movie", secondary=movie_keyword_association, back_populates="keywords")


class Actor(Base):
    """ORM model for an actor (cast member)."""

    __tablename__ = "actors"
    tmdb_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    profile_path = Column(String)
    gender = Column(Integer)
    movies = relationship("Movie", secondary=movie_actor_association, back_populates="actors")


class Director(Base):
    """ORM model for a movie director."""

    __tablename__ = "directors"
    tmdb_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    profile_path = Column(String)
    movies = relationship("Movie", secondary=movie_director_association, back_populates="directors")


class Crew(Base):
    """ORM model for a non-directing crew member."""

    __tablename__ = "crew"
    tmdb_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    profile_path = Column(String)
    movies = relationship("Movie", secondary=movie_crew_association, back_populates="crew")
