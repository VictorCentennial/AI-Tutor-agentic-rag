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

# Copy nginx configuration (optional, if you need custom config)

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]