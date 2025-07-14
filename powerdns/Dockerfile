# PowerDNS Authoritative Server with PostgreSQL Backend
FROM alpine:3.18

# Install PowerDNS and PostgreSQL client
RUN apk add --no-cache \
    pdns \
    pdns-backend-pgsql \
    postgresql-client \
    curl \
    bash \
    tzdata \
    gettext

# pdns user and group already exist in the Alpine pdns package

# Create necessary directories
RUN mkdir -p /etc/pdns/conf.d /var/run/pdns && \
    chown -R pdns:pdns /etc/pdns /var/run/pdns

# Copy configuration and entrypoint
COPY pdns.conf.template /etc/pdns/pdns.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose DNS and API ports
EXPOSE 53/tcp 53/udp 8053/tcp

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD pdns_control ping || exit 1

# Run as root to bind to privileged port 53
ENTRYPOINT ["/entrypoint.sh"]
CMD ["pdns_server", "--daemon=no", "--config-dir=/etc/pdns"]