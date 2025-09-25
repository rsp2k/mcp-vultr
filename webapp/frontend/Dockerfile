# Frontend Dockerfile for Astro + Alpine.js
FROM node:20-alpine AS base
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source files
COPY . .

# Development stage
FROM base AS development
EXPOSE 4321
CMD ["npm", "run", "dev"]

# Build stage
FROM base AS build
RUN npm run build

# Production stage with Caddy
FROM caddy:2-alpine AS production

# Copy built assets
COPY --from=build /app/dist /srv

# Copy Caddy configuration
COPY Caddyfile /etc/caddy/Caddyfile

# Add health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

EXPOSE 80
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]