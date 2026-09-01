# Frontend Dockerfile — React + Vite, built then served as static files by
# Nginx. Build context is frontend/ (see docker-compose.yml).

# ---- Stage 1: build the static production bundle ----
FROM node:22-alpine AS build
WORKDIR /app

# Install dependencies before copying source — this layer only rebuilds when
# package.json/package-lock.json actually change.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vite inlines import.meta.env.VITE_* values into the built JS at build time
# (they do not exist at container runtime), so this must be a build ARG.
# Defaults to a relative path so requests go through this same Nginx, which
# proxies /api/ and /health to the backend container — see nginx.conf.
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ---- Stage 2: serve the build with Nginx ----
FROM nginx:1.27-alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=10s \
    CMD wget --quiet --spider http://localhost/ || exit 1
