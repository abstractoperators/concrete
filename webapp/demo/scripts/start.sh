#!/bin/sh

cd /app
celery -A concrete worker --loglevel=INFO --detach

cd /app/webapp/demo
poetry run gunicorn server:app --bind 0.0.0.0:80 --workers 1 --worker-class uvicorn.workers.UvicornWorker --threads 1 --timeout=2000