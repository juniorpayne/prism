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

# Copy configuration
COPY pdns.conf /etc/pdns/pdns.conf
COPY entrypoint.sh /entrypoint.sh

# Make entrypoint executable
RUN chmod +x /entrypoint.sh

# Expose DNS and API ports
EXPOSE 53/tcp 53/udp 8053/tcp

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD pdns_control ping || exit 1

# Run as pdns user
USER pdns

ENTRYPOINT ["/entrypoint.sh"]
CMD ["pdns_server", "--daemon=no", "--disable-syslog", "--log-timestamp=yes", "--loglevel=4"]