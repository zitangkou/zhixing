#!/bin/sh
set -e

cd /app/server
mkdir -p data

uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 &

exec nginx -g 'daemon off;'
