# Movie Database

A simple movie database for educational purposes (practicing SQL joins, aggregations, pivots, etc.).

## Schema

4 tables: `directors`, `actors`, `movies`, `movie_actors` (junction table).

Data is fetched from [TMDb API](https://www.themoviedb.org/) (real movies, directors, actors).

## Prerequisites

- Python 3.10+
- Docker
- TMDb API key (free registration at https://www.themoviedb.org/settings/api)

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Create `.env` file

```
TMDB_API_KEY=your_tmdb_api_key
PG_HOST=localhost
PG_PORT=5435
PG_DBNAME=movie_db
PG_USER=movie_admin
PG_PASSWORD=test123
```

### 3. Start PostgreSQL

```bash
docker compose -p tmdb up -d
```

### 4. Populate the database

```bash
python populate.py
```

### Connect to the database

```bash
psql -h localhost -p 5435 -U movie_admin -d movie_db
```

## Usage

```bash
python populate.py [options]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--movies` | `-m` | 1000 | Number of movies to fetch |
| `--cast` | `-c` | 5 | Number of cast members per movie |

Examples:

```bash
python populate.py -m 500 -c 3
python populate.py --movies 2000 --cast 10
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TMDB_API_KEY` | (required) | TMDb API key |
| `PG_HOST` | `localhost` | PostgreSQL host |
| `PG_PORT` | `5435` | PostgreSQL port |
| `PG_DBNAME` | `movie_db` | PostgreSQL database name |
| `PG_USER` | `movie_admin` | PostgreSQL user |
| `PG_PASSWORD` | | PostgreSQL password |

## File structure

```
.
├── docker-compose.yaml    # PostgreSQL container
├── schema_postgres.sql    # PostgreSQL schema
├── populate.py            # Data fetcher script
└── .env                   # Environment variables (not committed)
```