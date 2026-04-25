FROM node:22-alpine AS build

WORKDIR /web

COPY web/package.json web/package-lock.json* ./
RUN npm install

COPY sources /sources
COPY web .
ARG VITE_API_BASE=
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build

FROM nginx:1.27-alpine

COPY web/deploy/docker-nginx-default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html

EXPOSE 80
