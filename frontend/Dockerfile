# Stage 1: Build
FROM node:18-alpine AS build-stage
WORKDIR /app
COPY package*.json ./

# Optimize npm for slow connections
RUN npm config set registry https://registry.npmmirror.com && \
    npm config set fetch-retry-maxtimeout 600000 && \
    npm config set fetch-retries 5 && \
    npm ci

COPY . .
RUN npm run build

# Stage 2: Production
FROM nginx:stable-alpine
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
