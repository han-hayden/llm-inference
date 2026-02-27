# Multi-stage build: Frontend + Backend + SSH
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Final image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    openssh-server \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Create admin user for SSH
RUN useradd -m -s /bin/bash admin

# Setup SSH
RUN mkdir -p /var/run/sshd
COPY docker/sshd_config /etc/ssh/sshd_config

# Install Python dependencies
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./

# Copy frontend build
COPY --from=frontend-build /app/frontend/dist /usr/share/nginx/html

# Copy nginx config
COPY docker/nginx.conf /etc/nginx/nginx.conf

# Copy supervisor config
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create data directory
RUN mkdir -p /data/results/reports && \
    chown -R admin:admin /data/results

# Entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080 8081 22

VOLUME ["/data/results"]

ENTRYPOINT ["/entrypoint.sh"]
CMD ["supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
