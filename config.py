import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

REQUEST_DELAY = 0.05  # 50ms between requests

# Postgres connection settings (from .env or environment)
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5435")
PG_DBNAME = os.getenv("PG_DBNAME", "movie_db")
PG_USER = os.getenv("PG_USER", "movie_admin")
PG_PASSWORD = os.getenv("PG_PASSWORD")


def get_db_connection():
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DBNAME,
        user=PG_USER, password=PG_PASSWORD
    )