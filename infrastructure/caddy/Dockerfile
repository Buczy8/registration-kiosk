# Stage 1: Build the frontend React Vite application
FROM node:22-alpine AS build-frontend
WORKDIR /app

# Copy packages manifests and install deterministic packages
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy the frontend source code
COPY frontend/ .

# Set up Vite build args and environment variables
ARG VITE_KIOSK_TOKEN
ARG VITE_KIOSK_IDLE_LOGOUT_SECONDS

ENV VITE_KIOSK_TOKEN=$VITE_KIOSK_TOKEN
ENV VITE_KIOSK_IDLE_LOGOUT_SECONDS=$VITE_KIOSK_IDLE_LOGOUT_SECONDS
ENV VITE_API_BASE_URL=/api/v1

# Compile optimized static build
RUN npm run build

# Stage 2: Caddy server to act as both reverse proxy and static asset server
FROM caddy:2.8-alpine

# Copy built static files to Caddy default root directory
COPY --from=build-frontend /app/dist /usr/share/caddy

# Copy Caddyfile configuration
COPY infrastructure/caddy/Caddyfile /etc/caddy/Caddyfile
