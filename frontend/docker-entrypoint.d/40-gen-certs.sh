#!/bin/sh
# Автогенерация самоподписанного HTTPS-сертификата для localhost.
# Скрипт помещается в /docker-entrypoint.d/ и ПОДКЛЮЧАЕТСЯ (source) entrypoint'ом
# официального nginx-образа, поэтому вместо exit используется return.
set -e

CERT_DIR=/etc/nginx/ssl
CERT=$CERT_DIR/balance.crt
KEY=$CERT_DIR/balance.key

mkdir -p "$CERT_DIR"

if [ -f "$CERT" ] && [ -f "$KEY" ]; then
    echo "[certs] Сертификаты найдены: $CERT"
    return 0
fi

if ! command -v openssl >/dev/null 2>&1; then
    echo "[certs] ОШИБКА: openssl не установлен в образе" >&2
    return 1
fi

openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
    -keyout "$KEY" \
    -out "$CERT" \
    -subj "/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1" \
    -addext "basicConstraints=CA:FALSE" \
    -addext "keyUsage=digitalSignature,keyEncipherment" \
    -addext "extendedKeyUsage=serverAuth" 2>/dev/null

# openssl старше 1.1.1 не понимает -addext — генерируем без расширений
if [ ! -f "$CERT" ]; then
    openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
        -keyout "$KEY" \
        -out "$CERT" \
        -subj "/CN=localhost"
fi

echo "[certs] Создан самоподписанный сертификат: $CERT (CN=localhost)"
return 0