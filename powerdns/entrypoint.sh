#!/bin/bash
set -e

echo "Starting PowerDNS Authoritative Server..."

# Wait for database to be ready
if [ -n "$PDNS_DB_HOST" ]; then
    echo "Waiting for PostgreSQL database at $PDNS_DB_HOST:${PDNS_DB_PORT:-5432}..."
    while ! pg_isready -h "$PDNS_DB_HOST" -p "${PDNS_DB_PORT:-5432}" -U "${PDNS_DB_USER:-powerdns}" -q; do
        echo "Database not ready yet. Waiting..."
        sleep 2
    done
    echo "Database is ready!"
fi

# Substitute environment variables in config
if [ -f /etc/pdns/pdns.conf ]; then
    # Create a temporary file with substituted variables
    envsubst < /etc/pdns/pdns.conf > /tmp/pdns.conf
    cat /tmp/pdns.conf > /etc/pdns/pdns.conf
    rm /tmp/pdns.conf
fi

# Verify API key is set
if [ -z "$PDNS_API_KEY" ]; then
    echo "WARNING: PDNS_API_KEY not set. API will not be accessible!"
fi

# Start PowerDNS
echo "Starting PowerDNS with command: $@"
exec "$@"