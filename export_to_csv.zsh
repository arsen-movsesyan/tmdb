#!/usr/bin/env zsh

# Ask for the postgres password once and reuse it for every table.
read -s "?Password for movie_admin: " PGPASSWORD
echo
export PGPASSWORD

tables=(directors actors movies movie_actors)

for table in $tables; do
    psql -U movie_admin -h localhost -p 5435 -d movie_db -c "\copy ${table} TO 'db-data/csv/${table}.csv' WITH CSV HEADER"
done

unset PGPASSWORD