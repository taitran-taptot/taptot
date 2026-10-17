FROM node:22-bookworm-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-bookworm-slim AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_OPTIONS=--max-old-space-size=3072
ARG NEXT_PUBLIC_API_BASE=http://api:8080/api/v1
ARG NEXT_PUBLIC_MEDIA_BASE=/media
ARG NEXT_PUBLIC_REQUIRE_REDEEM_CODE=true
ARG NEXT_PUBLIC_TURNSTILE_SITE_KEY=
ARG API_PROXY_TARGET=http://api:8080
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE \
    NEXT_PUBLIC_MEDIA_BASE=$NEXT_PUBLIC_MEDIA_BASE \
    NEXT_PUBLIC_REQUIRE_REDEEM_CODE=$NEXT_PUBLIC_REQUIRE_REDEEM_CODE \
    NEXT_PUBLIC_TURNSTILE_SITE_KEY=$NEXT_PUBLIC_TURNSTILE_SITE_KEY \
    API_PROXY_TARGET=$API_PROXY_TARGET
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-bookworm-slim AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
