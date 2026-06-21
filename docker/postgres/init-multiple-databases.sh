#!/bin/bash
set -euo pipefail

if [ -z "${POSTGRES_MULTIPLE_DATABASES:-}" ]; then
    echo "No additional databases requested"
    exit 0
fi

echo "Creating additional databases: ${POSTGRES_MULTIPLE_DATABASES}"

IFS=',' read -ra database_names <<< "${POSTGRES_MULTIPLE_DATABASES}"

for database_name in "${database_names[@]}"; do
    database_name="$(echo "${database_name}" | xargs)"

    if [ -z "${database_name}" ]; then
        continue
    fi

    echo "Creating database '${database_name}'"
    psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname postgres <<-EOSQL
        CREATE DATABASE "${database_name}";
EOSQL
done