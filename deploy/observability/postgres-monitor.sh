#!/bin/sh
# Creates or updates the read-only monitoring role the collector logs in with (pg_monitor: statistics views only, no
# table data). Runs as the database owner from docker-compose.yml. For a managed database, run the same two statements
# yourself (see the handbook, Operate, Observability).
set -eu
if [ -z "${MONITOR_PASSWORD:-}" ]; then
  echo "POSTGRES_MONITOR_PASSWORD is empty: no monitoring role created, Postgres server metrics stay off."
  exit 0
fi
psql -v ON_ERROR_STOP=1 -v user="$MONITOR_USER" -v pass="$MONITOR_PASSWORD" <<'SQL'
SELECT format(CASE WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'user')
                   THEN 'ALTER ROLE %I LOGIN PASSWORD %L' ELSE 'CREATE ROLE %I LOGIN PASSWORD %L' END, :'user', :'pass') \gexec
SELECT format('GRANT pg_monitor TO %I', :'user') \gexec
SQL
echo "Monitoring role $MONITOR_USER is ready."
