import os
import sys
import re
import time
import argparse
import requests
from config import REQUEST_DELAY, get_db_connection

OMDB_API_KEY = os.getenv("OMDB_API_KEY")
if not OMDB_API_KEY:
    print("Error: Set OMDB_API_KEY in .env file or environment.")
    sys.exit(1)

OMDB_URL = "http://www.omdbapi.com/"


def parse_awards(awards_text):
    """Parse OMDB Awards string into oscar_wins, total_wins, total_nominations."""
    if not awards_text or awards_text == "N/A":
        return 0, 0, 0

    oscar_wins = 0
    total_wins = 0
    total_nominations = 0

    oscar_match = re.search(r"Won (\d+) Oscar", awards_text)
    if oscar_match:
        oscar_wins = int(oscar_match.group(1))

    wins_match = re.search(r"(\d+) win", awards_text)
    if wins_match:
        total_wins = int(wins_match.group(1))

    noms_match = re.search(r"(\d+) nomination", awards_text)
    if noms_match:
        total_nominations = int(noms_match.group(1))

    return oscar_wins, total_wins, total_nominations


def fetch_omdb(imdb_id):
    """Fetch movie data from OMDB by IMDB ID."""
    time.sleep(REQUEST_DELAY)
    resp = requests.get(OMDB_URL, params={"i": imdb_id, "apikey": OMDB_API_KEY})
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Fetch awards data from OMDB API for movies missing it")
    parser.add_argument("-l", "--limit", type=int, default=1000, help="Max movies to process (default: 1000, OMDB free tier daily limit)")
    args = parser.parse_args()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, imdb_id FROM movies WHERE imdb_id IS NOT NULL AND oscar_wins IS NULL LIMIT %s",
        (args.limit,)
    )
    movies = cursor.fetchall()

    if not movies:
        print("No movies need awards data. All done!")
        return

    print(f"Fetching awards for {len(movies)} movies from OMDB...")

    processed = 0
    errors = 0
    for movie_id, imdb_id in movies:
        try:
            data = fetch_omdb(imdb_id)
            if data.get("Response") == "False":
                oscar_wins, total_wins, total_nominations = 0, 0, 0
            else:
                awards_text = data.get("Awards", "N/A")
                oscar_wins, total_wins, total_nominations = parse_awards(awards_text)

            cursor.execute(
                "UPDATE movies SET oscar_wins = %s, total_wins = %s, total_nominations = %s WHERE id = %s",
                (oscar_wins, total_wins, total_nominations, movie_id),
            )
            processed += 1
        except Exception as e:
            print(f"  Error for movie id={movie_id} ({imdb_id}): {e}")
            errors += 1

        if processed % 50 == 0 and processed > 0:
            print(f"  Processed {processed}/{len(movies)}...")
            conn.commit()

    conn.commit()
    conn.close()

    print(f"\nDone! Updated {processed} movies. Errors: {errors}")
    remaining_query = "SELECT COUNT(*) FROM movies WHERE imdb_id IS NOT NULL AND oscar_wins IS NULL"
    conn2 = get_db_connection()
    cur2 = conn2.cursor()
    cur2.execute(remaining_query)
    remaining = cur2.fetchone()[0]
    conn2.close()
    if remaining > 0:
        print(f"  Remaining movies without awards data: {remaining}")
        print(f"  Run this script again tomorrow to fetch the next batch.")
    else:
        print("  All movies now have awards data!")


if __name__ == "__main__":
    main()