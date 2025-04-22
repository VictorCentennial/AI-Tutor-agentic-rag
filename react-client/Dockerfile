FROM node:20-alpine as builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Stage 2: Serve the React app with Nginx (or any other web server)
FROM nginx:alpine

# Copy built React app from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy entrypoint script
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh && \
    sed -i 's/\r$//' /docker-entrypoint.sh

# Default environment variables (can be overridden at runtime)
ENV DEBUG_MODE=false
ENV SEMESTER_START_DATE="2025-01-08"
ENV TOTAL_WEEKS=14
ENV API_URL="http://127.0.0.1:5001"

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]