# ---- Node Builder Stage ----
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy application source
COPY . .

# Build Next.js application with standalone output
# Environment variables with NEXT_PUBLIC_ prefix must be set at build time
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ARG NEXT_PUBLIC_FLASK_API_URL
ARG NEXT_PUBLIC_AUTH_SERVICE_URL

ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_FLASK_API_URL=$NEXT_PUBLIC_FLASK_API_URL
ENV NEXT_PUBLIC_AUTH_SERVICE_URL=$NEXT_PUBLIC_AUTH_SERVICE_URL

# Build the application
RUN npm run build

# ---- Final Stage ----
FROM node:18-alpine AS runner

WORKDIR /app

# Set to production
ENV NODE_ENV=production

# Create a non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy necessary files from builder
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Switch to non-root user
USER nextjs

# Expose port
EXPOSE 3000

# Set hostname to 0.0.0.0 to allow external connections
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

# Start the application
CMD ["node", "server.js"]
