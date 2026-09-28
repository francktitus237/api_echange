#!/bin/sh
set -e

# Neutralize any DB env vars injected by the platform (e.g. DATABASE_URL/DB_HOST
# pointing to an external host that is not reachable from this network).
unset DATABASE_URL

if getent hosts db >/dev/null 2>&1; then
    echo "=== Using bundled PostgreSQL (db) ==="
    export USE_SQLITE=False
    export DB_NAME=forex_db
    export DB_USER=postgres
    export DB_PASSWORD=MonMotDePasseFort2026!
    export DB_HOST=db
    export DB_PORT=5432
else
    echo "=== 'db' host not resolvable, falling back to SQLite ==="
    export USE_SQLITE=True
    unset DB_HOST DB_NAME DB_USER DB_PASSWORD DB_PORT
fi

echo "=== Applying migrations ==="
python manage.py migrate --settings=forex_platform.settings --noinput

echo "=== Loading currencies fixture ==="
python manage.py loaddata currencies --settings=forex_platform.settings 2>/dev/null || true

echo "=== Starting services ==="
exec "$@"
