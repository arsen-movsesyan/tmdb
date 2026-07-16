CREATE TABLE directors (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    birth_date DATE,
    nationality VARCHAR(200)
);

CREATE TABLE actors (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    birth_date DATE,
    nationality VARCHAR(200)
);

CREATE TABLE movies (
    id SERIAL PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    release_year INTEGER,
    duration_min INTEGER,
    tmdb_rating NUMERIC(3, 1),
    country VARCHAR(100),
    budget BIGINT,
    box_office BIGINT,
    director_id INTEGER REFERENCES directors(id)
);

CREATE TABLE movie_actors (
    movie_id INTEGER NOT NULL REFERENCES movies(id),
    actor_id INTEGER NOT NULL REFERENCES actors(id),
    role_name VARCHAR(200),
    PRIMARY KEY (movie_id, actor_id)
);