#!/bin/sh

cd /app/webapp/daemons
uv run gunicorn server:app --bind 0.0.0.0:80 --workers 1 --worker-class uvicorn.workers.UvicornWorker --threads 1 --timeout=2000