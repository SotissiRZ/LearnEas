# --- LearnEas frontend (Next.js, build multi-étapes) ---

# 1) Installation des dépendances
FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund

# 2) Build de production
FROM node:20-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# URL de l'API injectée au build (les variables NEXT_PUBLIC_* sont figées côté client)
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api
ARG NEXT_PUBLIC_RTC_STUN_URL=stun:stun.l.google.com:19302
ARG NEXT_PUBLIC_RTC_TURN_URL=
ARG NEXT_PUBLIC_RTC_TURN_USERNAME=
ARG NEXT_PUBLIC_RTC_TURN_CREDENTIAL=
ARG NEXT_PUBLIC_MAX_VIDEO_UPLOAD_MB=2048
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_RTC_STUN_URL=$NEXT_PUBLIC_RTC_STUN_URL \
    NEXT_PUBLIC_RTC_TURN_URL=$NEXT_PUBLIC_RTC_TURN_URL \
    NEXT_PUBLIC_RTC_TURN_USERNAME=$NEXT_PUBLIC_RTC_TURN_USERNAME \
    NEXT_PUBLIC_RTC_TURN_CREDENTIAL=$NEXT_PUBLIC_RTC_TURN_CREDENTIAL \
    NEXT_PUBLIC_MAX_VIDEO_UPLOAD_MB=$NEXT_PUBLIC_MAX_VIDEO_UPLOAD_MB

RUN npm run build

# 3) Image finale, minimale (mode "standalone")
FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
