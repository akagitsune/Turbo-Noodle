"""Bulk ingestion of TMDB movie and credits CSV data into the SQLite database."""

import pandas as pd
import ast
import os
from datetime import datetime
from typing import Dict, List, Tuple

from src.data.database import db_connector
from src.data import models
from sqlalchemy import insert


class DataIngester:
    """
    Handles ingestion of movie data from CSV files into the database.
    Optimized for speed with bulk inserts and parallel processing.
    """

    BATCH_SIZE = 500  # Insert in batches of this size

    def __init__(self, db_connector):
        """Store the database connector used for all insert operations."""
        self.db = db_connector

    @staticmethod
    def safe_parse_json_list(text):
        """Parses TMDB JSON-like strings representing lists of dicts."""
        try:
            if pd.isna(text):
                return []
            if isinstance(text, str):
                return ast.literal_eval(text)
            return []
        except (ValueError, SyntaxError):
            return []

    @staticmethod
    def parse_date(date_str):
        """Parse date string to datetime object."""
        if pd.isna(date_str) or not date_str:
            return None
        try:
            return datetime.strptime(str(date_str), "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def extract_year(date_str):
        """Extract year from date string."""
        if pd.isna(date_str) or not date_str:
            return None
        try:
            return int(str(date_str).split('-')[0])
        except ValueError:
            return None

    def _bulk_insert_mappings(self, session, model, mappings: List[Dict]):
        """Bulk insert mappings into the database, skipping duplicates."""
        if not mappings:
            return
        for i in range(0, len(mappings), self.BATCH_SIZE):
            batch = mappings[i:i + self.BATCH_SIZE]
            session.execute(insert(model.__table__).prefix_with("OR IGNORE"), batch)
        session.commit()

    def _extract_entities_from_movies(self, df: pd.DataFrame) -> Tuple[List[Dict], Dict, Dict, Dict, Dict, Dict]:
        """
        Extract all entities from the movies dataframe.
        Returns movies and entity dictionaries for bulk insertion.
        """
        movies = []
        genres = {}  # tmdb_id -> data
        countries = {}  # iso_code -> data
        languages = {}  # iso_code -> data
        companies = {}  # tmdb_id -> data
        keywords = {}  # tmdb_id -> data

        for _, row in df.iterrows():
            movie_id = int(row.get('id')) if pd.notna(row.get('id')) else None
            if not movie_id:
                continue

            movie = {
                'tmdb_id': movie_id,
                'title': row.get('title', 'Unknown') if pd.notna(row.get('title')) else 'Unknown',
                'original_title': row.get('original_title') if pd.notna(row.get('original_title')) else None,
                'tagline': row.get('tagline') if pd.notna(row.get('tagline')) else None,
                'overview': row.get('overview') if pd.notna(row.get('overview')) else None,
                'homepage': row.get('homepage') if pd.notna(row.get('homepage')) else None,
                'status': row.get('status') if pd.notna(row.get('status')) else None,
                'release_date': self.parse_date(row.get('release_date')),
                'year': self.extract_year(row.get('release_date')),
                'runtime': float(row.get('runtime')) if pd.notna(row.get('runtime')) else None,
                'original_language_code': row.get('original_language') if pd.notna(row.get('original_language')) else None,
                'budget': int(row.get('budget')) if pd.notna(row.get('budget')) else None,
                'revenue': int(row.get('revenue')) if pd.notna(row.get('revenue')) else None,
                'popularity': float(row.get('popularity')) if pd.notna(row.get('popularity')) else None,
                'vote_average': float(row.get('vote_average')) if pd.notna(row.get('vote_average')) else None,
                'vote_count': int(row.get('vote_count')) if pd.notna(row.get('vote_count')) else None,
            }
            movies.append(movie)

            # Extract genres
            for g in self.safe_parse_json_list(row.get('genres')):
                tmdb_id = g.get('id')
                if tmdb_id and tmdb_id not in genres:
                    genres[tmdb_id] = {'tmdb_id': tmdb_id, 'name': g.get('name')}

            # Extract countries
            for c in self.safe_parse_json_list(row.get('production_countries')):
                iso_code = c.get('iso_3166_1')
                if iso_code and iso_code not in countries:
                    countries[iso_code] = {'iso_code': iso_code, 'name': c.get('name')}

            # Extract languages
            for lang in self.safe_parse_json_list(row.get('spoken_languages')):
                iso_code = lang.get('iso_639_1')
                if iso_code and iso_code not in languages:
                    languages[iso_code] = {'iso_code': iso_code, 'name': lang.get('name')}

            # Extract companies
            for c in self.safe_parse_json_list(row.get('production_companies')):
                tmdb_id = c.get('id')
                if tmdb_id and tmdb_id not in companies:
                    companies[tmdb_id] = {
                        'tmdb_id': tmdb_id,
                        'name': c.get('name'),
                        'logo_path': c.get('logo_path'),
                        'origin_country': c.get('origin_country')
                    }

            # Extract keywords
            for k in self.safe_parse_json_list(row.get('keywords')):
                tmdb_id = k.get('id')
                if tmdb_id and tmdb_id not in keywords:
                    keywords[tmdb_id] = {'tmdb_id': tmdb_id, 'name': k.get('name')}

        return movies, genres, countries, languages, companies, keywords

    def _extract_credits_data(self, credits_df: pd.DataFrame) -> Tuple[Dict, Dict, Dict, List[Dict], List[Dict], List[Dict]]:
        """
        Extract all credits data.
        Returns actors, directors, crew, and association data.
        """
        actors = {}  # tmdb_id -> data
        directors = {}  # tmdb_id -> data
        crew_members = {}  # tmdb_id -> data

        movie_actors = []  # (movie_id, actor_tmdb_id, character, order)
        movie_directors = []  # (movie_id, director_tmdb_id)
        movie_crew = []  # (movie_id, crew_tmdb_id, job, department)

        seen_actor_movies = set()
        seen_crew_jobs = set()
        seen_director_movies = set()

        for _, row in credits_df.iterrows():
            movie_id = int(row['movie_id']) if pd.notna(row['movie_id']) else None
            if not movie_id:
                continue

            # Process cast (actors)
            for cast_member in self.safe_parse_json_list(row.get('cast')):
                actor_tmdb_id = cast_member.get('id')
                name = cast_member.get('name')
                if actor_tmdb_id and name:
                    # Add actor to dict
                    if actor_tmdb_id not in actors:
                        actors[actor_tmdb_id] = {
                            'tmdb_id': actor_tmdb_id,
                            'name': name,
                            'profile_path': cast_member.get('profile_path'),
                            'gender': cast_member.get('gender')
                        }

                    # Add movie_actor association
                    actor_key = (movie_id, actor_tmdb_id)
                    if actor_key not in seen_actor_movies:
                        seen_actor_movies.add(actor_key)
                        movie_actors.append({
                            'movie_id': movie_id,
                            'actor_id': actor_tmdb_id,
                            'character_name': cast_member.get('character'),
                            'order': cast_member.get('order')
                        })

            # Process crew
            for crew_member in self.safe_parse_json_list(row.get('crew')):
                crew_tmdb_id = crew_member.get('id')
                name = crew_member.get('name')
                job = crew_member.get('job')
                department = crew_member.get('department')

                if crew_tmdb_id and name and job:
                    # Add crew member
                    if crew_tmdb_id not in crew_members:
                        crew_members[crew_tmdb_id] = {
                            'tmdb_id': crew_tmdb_id,
                            'name': name,
                            'profile_path': crew_member.get('profile_path')
                        }

                    # Add movie_crew association
                    crew_key = (movie_id, crew_tmdb_id, job)
                    if crew_key not in seen_crew_jobs:
                        seen_crew_jobs.add(crew_key)
                        movie_crew.append({
                            'movie_id': movie_id,
                            'crew_id': crew_tmdb_id,
                            'job': job,
                            'department': department
                        })

                    # Handle directors
                    if job == 'Director':
                        if crew_tmdb_id not in directors:
                            directors[crew_tmdb_id] = {
                                'tmdb_id': crew_tmdb_id,
                                'name': name,
                                'profile_path': crew_member.get('profile_path')
                            }

                        dir_key = (movie_id, crew_tmdb_id)
                        if dir_key not in seen_director_movies:
                            seen_director_movies.add(dir_key)
                            movie_directors.append({
                                'movie_id': movie_id,
                                'director_id': crew_tmdb_id
                            })

        return (actors, directors, crew_members, movie_actors, movie_directors, movie_crew)

    def run_ingestion_with_credits(self, movies_csv: str, credits_csv: str):
        """
        Optimized ingestion using bulk inserts.
        Reads both TMDB movies and credits CSVs to populate all normalized tables.
        """
        if not os.path.exists(movies_csv):
            print(f"Error: Could not find '{movies_csv}'.")
            return
        if not os.path.exists(credits_csv):
            print(f"Error: Could not find '{credits_csv}'.")
            return

        # Ensure tables are created
        print("Creating database tables...")
        self.db.base.metadata.create_all(self.db.engine)

        # Load movies data
        print("Loading movies data...")
        df = pd.read_csv(movies_csv)
        print(f"Loaded {len(df)} movies")

        # Extract entities from movies
        print("Extracting entities from movies...")
        movies, genres, countries, languages, companies, keywords = self._extract_entities_from_movies(df)

        # Load credits data
        print("Loading credits data...")
        credits_df = pd.read_csv(credits_csv)
        print(f"Loaded {len(credits_df)} credit entries")

        # Extract credits data
        print("Extracting cast and crew data...")
        (actors, directors, crew_members,
         movie_actors, movie_directors, movie_crew) = self._extract_credits_data(credits_df)

        # Get movie entity relationships from movies dataframe
        print("Building movie relationships...")
        movie_genres = []
        movie_countries = []
        movie_languages = []
        movie_companies = []
        movie_keywords_list = []

        for _, row in df.iterrows():
            movie_id = int(row.get('id')) if pd.notna(row.get('id')) else None
            if not movie_id:
                continue

            # Genres
            for g in self.safe_parse_json_list(row.get('genres')):
                tmdb_id = g.get('id')
                if tmdb_id:
                    movie_genres.append({'movie_id': movie_id, 'genre_id': tmdb_id})

            # Countries
            for c in self.safe_parse_json_list(row.get('production_countries')):
                iso = c.get('iso_3166_1')
                if iso:
                    movie_countries.append({'movie_id': movie_id, 'country_id': iso})

            # Languages
            for lang in self.safe_parse_json_list(row.get('spoken_languages')):
                iso = lang.get('iso_639_1')
                if iso:
                    movie_languages.append({'movie_id': movie_id, 'language_id': iso})

            # Companies
            for c in self.safe_parse_json_list(row.get('production_companies')):
                tmdb_id = c.get('id')
                if tmdb_id:
                    movie_companies.append({'movie_id': movie_id, 'company_id': tmdb_id})

            # Keywords
            for k in self.safe_parse_json_list(row.get('keywords')):
                tmdb_id = k.get('id')
                if tmdb_id:
                    movie_keywords_list.append({'movie_id': movie_id, 'keyword_id': tmdb_id})

        # Bulk insert everything
        session = self.db.get_db()

        print(f"\nBulk inserting {len(genres)} genres...")
        self._bulk_insert_mappings(session, models.Genre, list(genres.values()))

        print(f"Bulk inserting {len(countries)} countries...")
        self._bulk_insert_mappings(session, models.Country, list(countries.values()))

        print(f"Bulk inserting {len(languages)} languages...")
        self._bulk_insert_mappings(session, models.Language, list(languages.values()))

        print(f"Bulk inserting {len(companies)} companies...")
        self._bulk_insert_mappings(session, models.Company, list(companies.values()))

        print(f"Bulk inserting {len(keywords)} keywords...")
        self._bulk_insert_mappings(session, models.Keyword, list(keywords.values()))

        print(f"Bulk inserting {len(actors)} actors...")
        self._bulk_insert_mappings(session, models.Actor, list(actors.values()))

        print(f"Bulk inserting {len(directors)} directors...")
        self._bulk_insert_mappings(session, models.Director, list(directors.values()))

        print(f"Bulk inserting {len(crew_members)} crew members...")
        self._bulk_insert_mappings(session, models.Crew, list(crew_members.values()))

        print(f"\nBulk inserting {len(movies)} movies...")
        self._bulk_insert_mappings(session, models.Movie, movies)

        print(f"Bulk inserting {len(movie_genres)} movie-genre associations...")
        if movie_genres:
            for i in range(0, len(movie_genres), self.BATCH_SIZE):
                batch = movie_genres[i:i + self.BATCH_SIZE]
                session.execute(insert(models.movie_genre_association).prefix_with("OR IGNORE"), batch)
            session.commit()

        print(f"Bulk inserting {len(movie_countries)} movie-country associations...")
        if movie_countries:
            for i in range(0, len(movie_countries), self.BATCH_SIZE):
                batch = movie_countries[i:i + self.BATCH_SIZE]
                session.execute(insert(models.movie_country_association).prefix_with("OR IGNORE"), batch)
            session.commit()

        print(f"Bulk inserting {len(movie_languages)} movie-language associations...")
        if movie_languages:
            for i in range(0, len(movie_languages), self.BATCH_SIZE):
                batch = movie_languages[i:i + self.BATCH_SIZE]
                session.execute(insert(models.movie_language_association).prefix_with("OR IGNORE"), batch)
            session.commit()

        print(f"Bulk inserting {len(movie_companies)} movie-company associations...")
        if movie_companies:
            for i in range(0, len(movie_companies), self.BATCH_SIZE):
                batch = movie_companies[i:i + self.BATCH_SIZE]
                session.execute(insert(models.movie_company_association).prefix_with("OR IGNORE"), batch)
            session.commit()

        print(f"Bulk inserting {len(movie_keywords_list)} movie-keyword associations...")
        if movie_keywords_list:
            for i in range(0, len(movie_keywords_list), self.BATCH_SIZE):
                batch = movie_keywords_list[i:i + self.BATCH_SIZE]
                session.execute(insert(models.movie_keyword_association).prefix_with("OR IGNORE"), batch)
            session.commit()

        print(f"Bulk inserting {len(movie_actors)} movie-actor associations...")
        if movie_actors:
            for i in range(0, len(movie_actors), self.BATCH_SIZE):
                batch = movie_actors[i:i + self.BATCH_SIZE]
                session.execute(insert(models.movie_actor_association).prefix_with("OR IGNORE"), batch)
            session.commit()

        print(f"Bulk inserting {len(movie_directors)} movie-director associations...")
        if movie_directors:
            for i in range(0, len(movie_directors), self.BATCH_SIZE):
                batch = movie_directors[i:i + self.BATCH_SIZE]
                session.execute(insert(models.movie_director_association).prefix_with("OR IGNORE"), batch)
            session.commit()

        print(f"Bulk inserting {len(movie_crew)} movie-crew associations...")
        if movie_crew:
            for i in range(0, len(movie_crew), self.BATCH_SIZE):
                batch = movie_crew[i:i + self.BATCH_SIZE]
                session.execute(insert(models.movie_crew_association).prefix_with("OR IGNORE"), batch)
            session.commit()

        session.close()

        print("\n" + "=" * 50)
        print("Ingestion complete!")
        print(f"Movies: {len(movies):,}")
        print(f"Genres: {len(genres):,}")
        print(f"Actors: {len(actors):,}")
        print(f"Directors: {len(directors):,}")
        print(f"Countries: {len(countries):,}")
        print(f"Languages: {len(languages):,}")
        print(f"Crew: {len(crew_members):,}")
        print(f"Companies: {len(companies):,}")
        print(f"Keywords: {len(keywords):,}")
        print("=" * 50)


def run_ingestion_with_credits(movies_csv: str, credits_csv: str):
    """Ingest with all normalized tables using optimized bulk inserts."""
    ingester = DataIngester(db_connector)
    ingester.run_ingestion_with_credits(movies_csv, credits_csv)


if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser(description="Ingest TMDB movie data with normalized tables (optimized)")
    parser.add_argument("movies", help="Path to tmdb_5000_movies.csv")
    parser.add_argument("credits", help="Path to tmdb_5000_credits.csv")
    args = parser.parse_args()

    start_time = time.time()
    run_ingestion_with_credits(args.movies, args.credits)
    elapsed = time.time() - start_time
    print(f"\nTotal time: {elapsed:.2f} seconds")
