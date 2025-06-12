# Production Dockerfile for Prism DNS Web Interface
# Uses nginx to serve static files and proxy API requests

FROM nginx:1.25-alpine AS production

# Install curl for health checks
RUN apk add --no-cache curl

# Remove default nginx configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy nginx configuration
COPY nginx.simple.conf /etc/nginx/conf.d/default.conf

# Copy static web files
COPY index.html /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/
COPY js/ /usr/share/nginx/html/js/

# Set permissions for static files
RUN chmod -R 755 /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost/nginx-health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

# Development stage with live reload
FROM nginx:1.25-alpine AS development

# Install curl and basic tools
RUN apk add --no-cache curl inotify-tools

# Remove default nginx configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy development nginx config
COPY nginx.dev.conf /etc/nginx/conf.d/default.conf

# Create directory for live files
WORKDIR /usr/share/nginx/html

# Development-specific configuration
ENV NGINX_ENV=development

# Expose port 80
EXPOSE 80

# Development command (could include live reload)
CMD ["nginx", "-g", "daemon off;"]