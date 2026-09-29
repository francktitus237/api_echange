#!/bin/sh
set -e

# Neutralize any DB env vars injected by the platform (e.g. DATABASE_URL/DB_HOST
# pointing to an external host that is not reachable from this network).
unset DATABASE_URL

# Django refuses to boot with an empty SECRET_KEY when DEBUG=False.
# Generate an ephemeral one if the platform didn't provide it (sessions are
# invalidated on restart — set a fixed SECRET_KEY in Dokploy to avoid this).
if [ -z "$SECRET_KEY" ]; then
    export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
    echo "=== WARNING: SECRET_KEY not set — generated ephemeral key ==="
fi

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
                echo "=== WARNING: migrations failed 15x — starting services anyway ==="
                break
            fi
            echo "=== DB not ready, retry $retries/15 ==="
            sleep 3
        done

        echo "=== Collecting static files ==="
        python manage.py collectstatic --settings=forex_platform.settings --noinput || true

        echo "=== Loading currencies fixture ==="
        python manage.py loaddata currencies --settings=forex_platform.settings 2>/dev/null || true

        echo "=== Seeding forex providers & schedules ==="
        python manage.py seed_forex --settings=forex_platform.settings || true

        echo "=== First rates sync ==="
        echo "from apps.forex.tasks import sync_all_rates; sync_all_rates()" | python manage.py shell --settings=forex_platform.settings 2>/dev/null || true

        echo "=== Superuser setup (create or promote) ==="
        python manage.py setup_admin --settings=forex_platform.settings || true
        ;;
    *)
        echo "=== Skipping migrations (worker service) ==="
        ;;
esac

echo "=== Starting services ==="
exec "$@"
