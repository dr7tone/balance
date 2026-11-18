# --- Стадия сборки ---
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json ./
# package-lock.json отсутствует в репозитории — используем npm install
RUN npm install

COPY . .

RUN npm run build

# --- Стадия раздачи (nginx + HTTPS) ---
FROM nginx:1.27-alpine

# openssl нужен для автогенерации самоподписанного сертификата при старте
RUN apk add --no-cache openssl

COPY nginx.conf /etc/nginx/conf.d/default.conf
# Скрипты в /docker-entrypoint.d/ выполняются nginx-образом автоматически
COPY docker-entrypoint.d/ /docker-entrypoint.d/
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
