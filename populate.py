import os
import sys
import time
import sqlite3
import argparse
import requests
from dotenv import load_dotenv

load_dotenv()

try:
    import psycopg2
except ImportError:
    psycopg2 = None

API_KEY = os.getenv("TMDB_API_KEY")
if not API_KEY:
    print("Error: Set TMDB_API_KEY in .env file or environment.")
    sys.exit(1)

BASE_URL = "https://api.themoviedb.org/3"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "movies.db")

REQUEST_DELAY = 0.05  # 50ms between requests

# Database type: "sqlite" or "postgres"
DB_TYPE = os.getenv("DB_TYPE", "sqlite")

# Postgres connection settings (from .env or environment)
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DBNAME = os.getenv("PG_DBNAME", "movie_db")
PG_USER = os.getenv("PG_USER", "movie_admin")
PG_PASSWORD = os.getenv("PG_PASSWORD")


def api_get(endpoint, params=None):
    url = f"{BASE_URL}{endpoint}"
    if params is None:
        params = {}
    params["api_key"] = API_KEY
    time.sleep(REQUEST_DELAY)
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


def fetch_movie_list(total):
    """Fetch movie IDs from top_rated and popular endpoints."""
    movie_ids = []
    seen = set()

    for endpoint in ["/movie/top_rated", "/movie/popular"]:
        page = 1
        while len(movie_ids) < total:
            data = api_get(endpoint, {"page": page})
            results = data.get("results", [])
            if not results:
                break
            for m in results:
                if m["id"] not in seen:
                    seen.add(m["id"])
                    movie_ids.append(m["id"])
            page += 1
            if page > data.get("total_pages", 1):
                break

        if len(movie_ids) >= total:
            break

    return movie_ids[:total]


def fetch_movie_details(movie_id):
    """Fetch full movie details including credits."""
    details = api_get(f"/movie/{movie_id}", {"append_to_response": "credits"})
    return details


def fetch_person_details(person_id):
    """Fetch person birth_date and nationality."""
    data = api_get(f"/person/{person_id}")
    return {
        "birth_date": data.get("birthday"),
        "nationality": data.get("place_of_birth"),
    }


def split_name(full_name):
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def create_database(db_type="sqlite"):
    if db_type == "sqlite":
        schema_path = os.path.join(SCRIPT_DIR, "schema_sqlite.sql")
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        conn = sqlite3.connect(DB_PATH)
        with open(schema_path, "r") as f:
            conn.executescript(f.read())
    elif db_type == "postgres":
        if psycopg2 is None:
            print("Error: psycopg2 is not installed. Run: pip install psycopg2-binary")
            sys.exit(1)
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, dbname=PG_DBNAME,
            user=PG_USER, password=PG_PASSWORD
        )
        schema_path = os.path.join(SCRIPT_DIR, "schema_postgres.sql")
        with open(schema_path, "r") as f:
            cursor = conn.cursor()
            cursor.execute(f.read())
            conn.commit()
    else:
        print(f"Error: Unknown DB_TYPE '{db_type}'. Use 'sqlite' or 'postgres'.")
        sys.exit(1)
    return conn


def main():
    parser = argparse.ArgumentParser(description="Populate movie database from TMDb API")
    parser.add_argument("-m", "--movies", type=int, default=1000, help="Number of movies to fetch (default: 1000)")
    parser.add_argument("-c", "--cast", type=int, default=5, help="Number of cast members per movie (default: 5)")
    args = parser.parse_args()

    movies_to_fetch = args.movies
    cast_per_movie = args.cast

    db_type = DB_TYPE.lower()
    ph = "%s" if db_type == "postgres" else "?"

    print(f"Fetching list of {movies_to_fetch} movies...")
    movie_ids = fetch_movie_list(movies_to_fetch)
    print(f"Got {len(movie_ids)} movie IDs.")

    conn = create_database(db_type)
    cursor = conn.cursor()

    # Caches: tmdb_person_id -> local db id
    director_cache = {}  # tmdb_id -> directors.id
    actor_cache = {}     # tmdb_id -> actors.id
    person_details_cache = {}  # tmdb_id -> {birth_date, nationality}

    def get_person_details(person_id):
        if person_id not in person_details_cache:
            try:
                person_details_cache[person_id] = fetch_person_details(person_id)
            except Exception:
                person_details_cache[person_id] = {"birth_date": None, "nationality": None}
        return person_details_cache[person_id]

    def get_or_create_person(person_id, name, table, cache):
        if person_id in cache:
            return cache[person_id]
        first_name, last_name = split_name(name)
        person_info = get_person_details(person_id)
        cursor.execute(
            f"INSERT INTO {table} (first_name, last_name, birth_date, nationality) VALUES ({ph}, {ph}, {ph}, {ph}) RETURNING id",
            (first_name, last_name, person_info["birth_date"], person_info["nationality"]),
        )
        db_id = cursor.fetchone()[0]
        cache[person_id] = db_id
        return db_id

    processed = 0
    for movie_id in movie_ids:
        try:
            details = fetch_movie_details(movie_id)
        except Exception as e:
            print(f"  Skipping movie {movie_id}: {e}")
            continue

        title = details.get("title")
        release_date = details.get("release_date", "")
        release_year = int(release_date[:4]) if release_date and len(release_date) >= 4 else None
        duration_min = details.get("runtime")
        tmdb_rating = details.get("vote_average")
        production_countries = details.get("production_countries", [])
        country = production_countries[0]["name"] if production_countries else None
        budget = details.get("budget") or None
        box_office = details.get("revenue") or None

        # Find director from crew
        movie_credits = details.get("credits", {})
        crew = movie_credits.get("crew", [])
        director_id = None
        for member in crew:
            if member.get("job") == "Director":
                director_id = get_or_create_person(member["id"], member["name"], "directors", director_cache)
                break

        cursor.execute(
            f"INSERT INTO movies (title, release_year, duration_min, tmdb_rating, country, budget, box_office, director_id) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}) RETURNING id",
            (title, release_year, duration_min, tmdb_rating, country, budget, box_office, director_id),
        )
        local_movie_id = cursor.fetchone()[0]

        # Insert cast
        cast = movie_credits.get("cast", [])[:cast_per_movie]
        for member in cast:
            actor_db_id = get_or_create_person(member["id"], member["name"], "actors", actor_cache)
            role_name = member.get("character")
            if db_type == "postgres":
                cursor.execute(
                    f"INSERT INTO movie_actors (movie_id, actor_id, role_name) VALUES ({ph}, {ph}, {ph}) ON CONFLICT DO NOTHING",
                    (local_movie_id, actor_db_id, role_name),
                )
            else:
                cursor.execute(
                    f"INSERT OR IGNORE INTO movie_actors (movie_id, actor_id, role_name) VALUES ({ph}, {ph}, {ph})",
                    (local_movie_id, actor_db_id, role_name),
                )

        processed += 1
        if processed % 50 == 0:
            print(f"  Processed {processed}/{len(movie_ids)} movies...")
            conn.commit()

    conn.commit()
    conn.close()

    print(f"\nDone! {db_type.upper()} database populated.")
    print(f"  Movies: {processed}")
    print(f"  Directors: {len(director_cache)}")
    print(f"  Actors: {len(actor_cache)}")


if __name__ == "__main__":
    main()