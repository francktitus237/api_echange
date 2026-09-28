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

# Only the main app container (supervisord) performs the deploy-time setup.
# Celery services share this entrypoint but must not run migrate concurrently.
case "$*" in
    *supervisord*)
        echo "=== Applying migrations (with DB wait) ==="
        retries=0
        until python manage.py migrate --settings=forex_platform.settings --noinput; do
            retries=$((retries + 1))
            if [ "$retries" -ge 15 ]; then
                echo "=== Database unreachable after 15 tries ==="
                exit 1
            fi
            echo "=== DB not ready, retry $retries/15 ==="
            sleep 3
        done

        echo "=== Collecting static files ==="
        python manage.py collectstatic --settings=forex_platform.settings --noinput || true

        echo "=== Loading currencies fixture ==="
        python manage.py loaddata currencies --settings=forex_platform.settings 2>/dev/null || true

        # Optional: auto-create superuser when env vars are provided
        if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
            echo "=== Creating superuser ==="
            python manage.py createsuperuser --settings=forex_platform.settings --noinput || true
        fi
        ;;
    *)
        echo "=== Skipping migrations (worker service) ==="
        ;;
esac

echo "=== Starting services ==="
exec "$@"
