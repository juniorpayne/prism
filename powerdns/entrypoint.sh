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

# Set defaults for environment variables
export PDNS_API_KEY=${PDNS_API_KEY:-changeme}
export PDNS_DB_HOST=${PDNS_DB_HOST:-localhost}
export PDNS_DB_PORT=${PDNS_DB_PORT:-5432}
export PDNS_DB_NAME=${PDNS_DB_NAME:-powerdns}
export PDNS_DB_USER=${PDNS_DB_USER:-powerdns}
export PDNS_DB_PASSWORD=${PDNS_DB_PASSWORD:-changeme}
export PDNS_API_ALLOW_FROM=${PDNS_API_ALLOW_FROM:-127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16}

# Substitute environment variables in config template
echo "Generating PowerDNS configuration from template..."
envsubst < /etc/pdns/pdns.conf.template > /etc/pdns/pdns.conf

# Replace ENV_ prefixed variables with actual values
sed -i "s/ENV_PDNS_API_KEY/$PDNS_API_KEY/g" /etc/pdns/pdns.conf
sed -i "s/ENV_PDNS_DB_HOST/$PDNS_DB_HOST/g" /etc/pdns/pdns.conf
sed -i "s/ENV_PDNS_DB_PORT/$PDNS_DB_PORT/g" /etc/pdns/pdns.conf
sed -i "s/ENV_PDNS_DB_NAME/$PDNS_DB_NAME/g" /etc/pdns/pdns.conf
sed -i "s/ENV_PDNS_DB_USER/$PDNS_DB_USER/g" /etc/pdns/pdns.conf
sed -i "s/ENV_PDNS_DB_PASSWORD/$PDNS_DB_PASSWORD/g" /etc/pdns/pdns.conf
sed -i "s/ENV_PDNS_API_ALLOW_FROM/$PDNS_API_ALLOW_FROM/g" /etc/pdns/pdns.conf

echo "PowerDNS configuration generated successfully."

# Verify API key is set
if [ -z "$PDNS_API_KEY" ]; then
    echo "WARNING: PDNS_API_KEY not set. API will not be accessible!"
fi

# Start PowerDNS
echo "Starting PowerDNS with command: $@"
exec "$@"